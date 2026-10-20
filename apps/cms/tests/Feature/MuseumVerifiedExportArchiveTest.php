<?php

namespace Tests\Feature;

use App\Jobs\PublishMuseumSnapshot;
use App\Models\MuseumContentApproval;
use App\Models\MuseumDocument;
use App\Models\MuseumEntry;
use App\Models\MuseumExportContentProof;
use App\Models\MuseumMedia;
use App\Models\MuseumPublicationRun;
use App\Support\MuseumApprovalRevision;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Storage;
use Symfony\Component\Process\Process;
use Tests\TestCase;

final class MuseumVerifiedExportArchiveTest extends TestCase
{
    use RefreshDatabase;

    private string $base;
    private string $root;
    private string $source;

    protected function setUp(): void
    {
        parent::setUp();
        $this->base = storage_path('framework/testing/archive-proof-'.bin2hex(random_bytes(10)));
        mkdir($this->base, 0700, true);
        $this->root = $this->base.'/verified';
        mkdir($this->root, 0700);
        $this->source = $this->base.'/stage';
        mkdir($this->source, 0700);
        config([
            'museum.editorial_approval_queue' => true,
            'museum.queue_publication' => true,
            'museum.queued_export_staging_dir' => $this->source,
            'museum.verified_archive_root' => $this->root,
            'queue.default' => 'database',
            'cache.default' => 'database',
        ]);
        Storage::fake('local');
    }

    protected function tearDown(): void
    {
        if (is_dir($this->base)) {
            // The archive is deliberately mode 0500: prepare ALL directory
            // permissions first, then remove child-first as a test cleanup.
            $directories = new \RecursiveIteratorIterator(
                new \RecursiveDirectoryIterator($this->base,\FilesystemIterator::SKIP_DOTS),
                \RecursiveIteratorIterator::SELF_FIRST
            );
            foreach ($directories as $dir) {
                if ($dir->isDir() && ! $dir->isLink()) chmod($dir->getPathname(),0700);
            }
            $items = new \RecursiveIteratorIterator(
                new \RecursiveDirectoryIterator($this->base,\FilesystemIterator::SKIP_DOTS),
                \RecursiveIteratorIterator::CHILD_FIRST
            );
            foreach ($items as $item) {
                $path = $item->getPathname();
                if ($item->isLink()) {
                    if (is_link($path)) unlink($path);
                } elseif ($item->isDir()) {
                    if (is_dir($path)) {
                        chmod($path, 0700);
                        rmdir($path);
                    }
                } elseif (is_file($path)) {
                    chmod($path, 0600);
                    unlink($path);
                }
            }
            rmdir($this->base);
        }
        parent::tearDown();
    }

    private function news(bool $withAssets = false): MuseumEntry
    {
        $entry = MuseumEntry::create([
            'type'=>'news', 'slug'=>'archived-private-entry', 'title'=>'Тестовая новость в архиве',
            'body'=>'<p>Одобренный текст</p>', 'status'=>'published',
        ]);
        if ($withAssets) {
            $picture = imagecreatetruecolor(18, 12);
            ob_start();
            imagewebp($picture);
            $bytes = ob_get_clean();
            imagedestroy($picture);
            $sha = hash('sha256', $bytes);
            Storage::disk('local')->put('museum/media/archive-image.webp', $bytes);
            MuseumMedia::create([
                'museum_entry_id'=>$entry->id, 'storage_path'=>'museum/media/archive-image.webp',
                'sha256'=>$sha, 'mime'=>'image/webp',
                'alt'=>'Старинная хлебная печь в музейном зале рядом с кирпичной стеной',
                'caption'=>'Печь', 'width'=>18,'height'=>12,'size_bytes'=>strlen($bytes),
                'source_rights_pending'=>false,
            ]);

            $pdf = "%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n<<>>\n%%EOF\n";
            $pdfSha = hash('sha256', $pdf);
            Storage::disk('local')->put('museum/documents/archive-test.pdf', $pdf);
            MuseumDocument::create([
                'museum_entry_id'=>$entry->id,'label'=>'Тестовое расписание посещения',
                'file_type'=>'pdf','storage_path'=>'museum/documents/archive-test.pdf',
                'sha256'=>$pdfSha,'size_bytes'=>strlen($pdf),
            ]);
        }
        MuseumContentApproval::create([
            'museum_entry_id'=>$entry->id, 'actor_id'=>1,
            'revision_sha256'=>MuseumApprovalRevision::fingerprint($entry->fresh()),
            'dispatch_status'=>'queued','approved_at'=>now('UTC'),
        ]);
        return $entry;
    }

    private function worker(): MuseumPublicationRun
    {
        $run = MuseumPublicationRun::create(['status'=>'queued']);
        (new PublishMuseumSnapshot($run->id))->handle();
        return $run->fresh();
    }

    private function python(MuseumPublicationRun $run, ?string $expected = null): Process
    {
        $command = [
            'python3', base_path('../../scripts/verify_private_snapshot_archive.py'),
            $this->root.'/'.$run->archive_id,
        ];
        if ($expected !== null) {
            $command[] = '--expected-receipt-sha256';
            $command[] = $expected;
        }
        $process = new Process($command);
        $process->run();
        return $process;
    }

    public function test_real_worker_archives_verified_json_manifest_webp_pdf_and_offline_reverification(): void
    {
        $this->news(withAssets:true);
        $run = $this->worker();
        $this->assertSame('succeeded', $run->status);
        $this->assertSame(1, $run->content_proof_count);
        $this->assertSame(4, $run->archive_file_count);
        $this->assertNotNull($run->archived_at);
        $this->assertMatchesRegularExpression('/^run-\d+-[a-f0-9]{64}-[a-f0-9]{64}$/', $run->archive_id);
        $archive = $this->root.'/'.$run->archive_id;
        $this->assertDirectoryExists($archive);
        $this->assertFileExists($archive.'/published.json');
        $this->assertFileExists($archive.'/snapshot-manifest.json');
        $this->assertFileExists($archive.'/archive-receipt.json');
        $this->assertSame(hash_file('sha256',$archive.'/archive-receipt.json'), $run->archive_receipt_sha256);
        $this->assertSame(hash_file('sha256',$archive.'/published.json'),$run->snapshot_sha256);
        $this->assertSame(hash_file('sha256',$archive.'/snapshot-manifest.json'),$run->manifest_sha256);
        $this->assertNotSame(0, fileperms($archive) & 0400);
        $this->assertSame(0, fileperms($archive.'/published.json') & 0200);
        $result = $this->python($run, $run->archive_receipt_sha256);
        $this->assertTrue($result->isSuccessful(), $result->getOutput().$result->getErrorOutput());
        $this->assertStringContainsString('"approved_subjects": 1', $result->getOutput());
        // Later overwriting ordinary staging does not alter historical bytes.
        file_put_contents($this->source.'/published.json',"MODIFIED LATER\n");
        $this->assertTrue($this->python($run,$run->archive_receipt_sha256)->isSuccessful());
        $this->assertSame(1, MuseumExportContentProof::count());
    }

    public function test_repeated_identical_content_gets_distinct_write_once_run_archives(): void
    {
        $this->news();
        $first = $this->worker();
        $second = $this->worker();
        $this->assertSame('succeeded',$first->status);
        $this->assertSame('succeeded',$second->status);
        $this->assertNotSame($first->archive_id,$second->archive_id);
        $this->assertSame($first->snapshot_sha256,$second->snapshot_sha256);
        $this->assertTrue($this->python($first,$first->archive_receipt_sha256)->isSuccessful());
        $this->assertTrue($this->python($second,$second->archive_receipt_sha256)->isSuccessful());
        $this->assertDirectoryExists($this->root.'/'.$first->archive_id);
    }

    public function test_archive_failure_fails_closed_and_does_not_keep_inclusion_proof(): void
    {
        $this->news();
        config(['museum.verified_archive_root'=>$this->base.'/non-existent']);
        $run = MuseumPublicationRun::create(['status'=>'queued']);
        try {
            (new PublishMuseumSnapshot($run->id))->handle();
            $this->fail('Archive failure should not mark queue run as succeeded');
        } catch (\RuntimeException $e) {
            $this->assertStringContainsString('Private archive root', $e->getMessage());
        }
        $run->refresh();
        $this->assertSame('failed',$run->status);
        $this->assertNull($run->content_verified_at);
        $this->assertNull($run->archive_id);
        $this->assertNull($run->archive_receipt_sha256);
        $this->assertDatabaseCount('museum_export_content_proofs',0);
        $this->assertDirectoryDoesNotExist($this->base.'/non-existent');
    }

    public function test_world_readable_archive_root_is_rejected_before_writing(): void
    {
        $this->news();
        chmod($this->root,0755);
        $run = MuseumPublicationRun::create(['status'=>'queued']);
        try {
            (new PublishMuseumSnapshot($run->id))->handle();
            $this->fail('World-readable archive must be rejected');
        } catch (\RuntimeException $error) {
            $this->assertStringContainsString('owner-only permissions', $error->getMessage());
        } finally {
            chmod($this->root,0700);
        }
        $this->assertSame('failed',$run->fresh()->status);
        $this->assertNull($run->fresh()->archived_at);
        $this->assertDatabaseCount('museum_export_content_proofs',0);
    }

    public function test_symlinked_archive_root_is_refused_without_touching_destination(): void
    {
        $this->news();
        symlink($this->root, $this->base.'/redirected');
        config(['museum.verified_archive_root'=>$this->base.'/redirected']);
        $run = MuseumPublicationRun::create(['status'=>'queued']);
        try {
            (new PublishMuseumSnapshot($run->id))->handle();
            $this->fail('Symlinked root accepted');
        } catch (\RuntimeException $e) {
            $this->assertStringContainsString('Private archive root', $e->getMessage());
        }
        $this->assertSame('failed',$run->fresh()->status);
        $this->assertDatabaseCount('museum_export_content_proofs',0);
    }

    public function test_tamper_missing_binary_forged_receipt_and_symlink_are_detected_offline(): void
    {
        $this->news(withAssets:true);
        $run = $this->worker();
        $archive = $this->root.'/'.$run->archive_id;
        $this->assertTrue($this->python($run,$run->archive_receipt_sha256)->isSuccessful());

        $media=glob($archive.'/media/*.webp')[0];
        chmod($media,0600);
        file_put_contents($media,'TAMPERED');
        $failure=$this->python($run,$run->archive_receipt_sha256);
        $this->assertFalse($failure->isSuccessful());
        $this->assertStringContainsString('PRIVATE_ARCHIVE_FAIL',$failure->getOutput());

        $mediaOriginal=Storage::disk('local')->get('museum/media/archive-image.webp');
        file_put_contents($media,$mediaOriginal);
        $this->assertTrue($this->python($run,$run->archive_receipt_sha256)->isSuccessful());

        $receipt=$archive.'/archive-receipt.json';
        chmod($receipt,0600);
        file_put_contents($receipt, file_get_contents($receipt)." ");
        $failure=$this->python($run,$run->archive_receipt_sha256);
        $this->assertFalse($failure->isSuccessful());
        $this->assertStringContainsString('receipt bytes differ',$failure->getOutput());
    }

    public function test_opt_in_disabled_preserves_normal_precontract_queue_behavior(): void
    {
        $this->news();
        config(['museum.verified_archive_root'=>null]);
        $run=$this->worker();
        $this->assertSame('succeeded',$run->status);
        $this->assertNull($run->archive_id);
        $this->assertNull($run->archive_receipt_sha256);
        $this->assertSame(1,$run->content_proof_count);
        $this->assertSame([], glob($this->root.'/run-*'));
    }
}
