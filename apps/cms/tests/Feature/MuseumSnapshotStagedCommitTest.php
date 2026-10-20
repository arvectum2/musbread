<?php

namespace Tests\Feature;

use App\Support\MuseumSnapshotSerializer;
use App\Support\MuseumSnapshotStagedCommit;
use Illuminate\Support\Facades\File;
use RuntimeException;
use Tests\TestCase;

class MuseumSnapshotStagedCommitTest extends TestCase
{
    private string $root;
    private MuseumSnapshotStagedCommit $transaction;

    protected function setUp(): void
    {
        parent::setUp();
        $this->transaction = app(MuseumSnapshotStagedCommit::class);
        $this->root = storage_path('framework/testing/staged-commit-'.bin2hex(random_bytes(8)));
        File::ensureDirectoryExists($this->root);
    }

    protected function tearDown(): void
    {
        if (isset($this->root)) File::deleteDirectory($this->root);
        parent::tearDown();
    }

    private function fixture(): array
    {
        $dir = $this->root;
        $stage = $this->transaction->begin();
        $oldMedia = str_repeat('a', 64).'.webp';
        $oldDocument = str_repeat('b', 64).'.pdf';
        $newMediaBytes = 'test-public-approved-WebP';
        $newDocumentBytes = 'test-approved-public-document';
        $newMedia = hash('sha256', $newMediaBytes).'.webp';
        $newDocument = hash('sha256', $newDocumentBytes).'.pdf';
        File::ensureDirectoryExists($dir.'/media');
        File::ensureDirectoryExists($dir.'/documents');
        File::ensureDirectoryExists($stage.'/media');
        File::ensureDirectoryExists($stage.'/documents');
        file_put_contents($dir.'/published.json', "approved-old-payload\n");
        file_put_contents($dir.'/manifest.json', "approved-old-manifest\n");
        file_put_contents($dir.'/media/'.$oldMedia, 'prior-media');
        file_put_contents($dir.'/documents/'.$oldDocument, 'prior-doc');
        file_put_contents($dir.'/media/custom-cover.webp', 'MUST_BE_PRESERVED');
        file_put_contents($stage.'/media/'.$newMedia, $newMediaBytes);
        file_put_contents($stage.'/documents/'.$newDocument, $newDocumentBytes);

        $media = ['media/'.$newMedia => ['sha256' => hash('sha256', $newMediaBytes), 'bytes' => strlen($newMediaBytes)]];
        $documents = ['documents/'.$newDocument => ['sha256' => hash('sha256', $newDocumentBytes), 'bytes' => strlen($newDocumentBytes)]];
        $serial = app(MuseumSnapshotSerializer::class);
        $payload = $serial->encode(['schema_version' => 1, 'entries' => [], 'events' => []]);
        file_put_contents($stage.'/published.json', $payload);
        file_put_contents($stage.'/snapshot-manifest.json',
            $serial->manifest($payload, $media, $documents, 0, 0, null));

        return compact('stage', 'dir', 'oldMedia', 'oldDocument', 'newMedia',
            'newDocument', 'media', 'documents', 'payload');
    }

    private function commit(array $f, ?callable $onStep = null): void
    {
        $this->transaction->commit(
            $f['stage'], $f['dir'].'/published.json', $f['dir'].'/manifest.json',
            $f['dir'].'/media', $f['dir'].'/documents', $f['media'], $f['documents'], $onStep
        );
    }

    private function assertOldRestored(array $f): void
    {
        $d = $f['dir'];
        $this->assertSame("approved-old-payload\n", file_get_contents($d.'/published.json'));
        $this->assertSame("approved-old-manifest\n", file_get_contents($d.'/manifest.json'));
        $this->assertSame('prior-media', file_get_contents($d.'/media/'.$f['oldMedia']));
        $this->assertSame('prior-doc', file_get_contents($d.'/documents/'.$f['oldDocument']));
        $this->assertFileDoesNotExist($d.'/media/'.$f['newMedia']);
        $this->assertFileDoesNotExist($d.'/documents/'.$f['newDocument']);
        $this->assertSame('MUST_BE_PRESERVED', file_get_contents($d.'/media/custom-cover.webp'));
    }

    public function test_prepared_assets_and_snapshot_commit_then_withdraw_only_old_hashed_files(): void
    {
        $f = $this->fixture();
        try {
            $this->commit($f);
            $this->assertSame($f['payload'], file_get_contents($f['dir'].'/published.json'));
            $manifest = json_decode(file_get_contents($f['dir'].'/manifest.json'), true);
            $this->assertSame(hash('sha256', $f['payload']), $manifest['files']['published.json']['sha256']);
            $this->assertSame('test-public-approved-WebP', file_get_contents($f['dir'].'/media/'.$f['newMedia']));
            $this->assertSame('test-approved-public-document', file_get_contents($f['dir'].'/documents/'.$f['newDocument']));
            $this->assertFileDoesNotExist($f['dir'].'/media/'.$f['oldMedia']);
            $this->assertFileDoesNotExist($f['dir'].'/documents/'.$f['oldDocument']);
            $this->assertSame('MUST_BE_PRESERVED', file_get_contents($f['dir'].'/media/custom-cover.webp'));
        } finally {
            $this->transaction->cleanup($f['stage']);
            $this->assertDirectoryDoesNotExist($f['stage']);
        }
    }

    public function test_injected_failure_at_every_phase_restores_old_files_and_manifest(): void
    {
        // 4 writes: media, document, manifest, JSON; 2 withdrawals.
        foreach (range(1, 6) as $abortAfter) {
            $f = $this->fixture();
            $counter = 0;
            try {
                try {
                    $this->commit($f, static function (string $phase) use (&$counter, $abortAfter): void {
                        $counter++;
                        if ($counter === $abortAfter) throw new RuntimeException('Injected failure: '.$phase);
                    });
                    $this->fail('Failure injection was not reached: '.$abortAfter);
                } catch (RuntimeException $error) {
                    $this->assertStringContainsString('Injected failure:', $error->getMessage());
                }
                $this->assertSame($abortAfter, $counter);
                $this->assertOldRestored($f);
            } finally {
                $this->transaction->cleanup($f['stage']);
                $this->assertDirectoryDoesNotExist($f['stage']);
            }
        }
    }

    public function test_corrupted_stage_file_is_refused_before_any_public_mutation(): void
    {
        $f = $this->fixture();
        try {
            file_put_contents($f['stage'].'/media/'.$f['newMedia'], 'tampered-staged-asset');
            try {
                $this->commit($f);
                $this->fail('Expected staged SHA rejection');
            } catch (RuntimeException $error) {
                $this->assertStringContainsString('integrity verification', $error->getMessage());
            }
            $this->assertOldRestored($f);
        } finally {
            $this->transaction->cleanup($f['stage']);
        }
    }

    public function test_parent_directory_symlink_is_rejected_without_touching_private_files(): void
    {
        $f = $this->fixture();
        try {
            $outside = $f['dir'].'/private-folder';
            File::ensureDirectoryExists($outside);
            file_put_contents($outside.'/do-not-touch', 'PRIVATE');
            symlink($outside, $f['dir'].'/media-link');
            try {
                $this->transaction->commit(
                    $f['stage'], $f['dir'].'/published.json', $f['dir'].'/manifest.json',
                    $f['dir'].'/media-link', $f['dir'].'/documents',
                    $f['media'], $f['documents']
                );
                $this->fail('Symlinked parent must not be writable');
            } catch (RuntimeException $e) {
                $this->assertStringContainsString('Unsafe export destination', $e->getMessage());
            }
            $this->assertSame('PRIVATE', file_get_contents($outside.'/do-not-touch'));
            $this->assertOldRestored($f);
        } finally {
            $this->transaction->cleanup($f['stage']);
        }
    }

    public function test_public_destination_symlink_cannot_redirect_publication(): void
    {
        $f = $this->fixture();
        try {
            $outside = $f['dir'].'/private-do-not-modify';
            file_put_contents($outside, 'PRIVATE');
            // The manifest destination itself must never redirect to a
            // private user file through a symlink.
            unlink($f['dir'].'/manifest.json');
            symlink($outside, $f['dir'].'/manifest.json');
            $this->expectException(RuntimeException::class);
            $this->expectExceptionMessage('Unsafe export destination');
            $this->commit($f);
        } finally {
            $this->assertSame('PRIVATE', file_get_contents($f['dir'].'/private-do-not-modify'));
            $this->assertSame("approved-old-payload\n", file_get_contents($f['dir'].'/published.json'));
            $this->transaction->cleanup($f['stage']);
        }
    }
}
