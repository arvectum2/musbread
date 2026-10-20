<?php

namespace Tests\Feature;

use App\Models\MuseumContentApproval;
use App\Models\MuseumEntry;
use App\Models\MuseumExportContentProof;
use App\Models\MuseumPublicationRun;
use App\Support\MuseumApprovalRevision;
use App\Support\MuseumExportContentVerifier;
use App\Support\MuseumSnapshotSerializer;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Artisan;
use Tests\TestCase;

final class MuseumExportContentVerifierTest extends TestCase
{
    use RefreshDatabase;

    private string $base;
    private MuseumEntry $entry;

    protected function setUp(): void
    {
        parent::setUp();
        $this->base = storage_path('framework/testing/proof-'.bin2hex(random_bytes(7)));
        mkdir($this->base, 0700, true);
        config([
            'museum.editorial_approval_queue' => true,
            'museum.queue_publication' => true,
            'queue.default' => 'database',
            'cache.default' => 'database',
        ]);
        $this->entry = MuseumEntry::create([
            'type' => 'news',
            'slug' => 'verified-museum-news',
            'title' => 'Настоящая тестовая новость',
            'excerpt' => 'Синтетический анонс',
            'body' => '<p>Точно одобренный текст</p>',
            'status' => 'published',
        ]);
        MuseumContentApproval::create([
            'museum_entry_id' => $this->entry->id,
            'actor_id' => 1,
            'revision_sha256' => MuseumApprovalRevision::fingerprint($this->entry->fresh()),
            'dispatch_status' => 'queued',
            'approved_at' => now('UTC'),
        ]);
        $this->assertSame(0, Artisan::call('museum:export', [
            '--output' => $this->snapshot(),
            '--manifest' => $this->manifest(),
            '--media-output-dir' => $this->base.'/media',
            '--document-output-dir' => $this->base.'/documents',
        ]), Artisan::output());
    }

    protected function tearDown(): void
    {
        foreach (glob($this->base.'/*') ?: [] as $file) {
            if (is_file($file)) unlink($file);
            elseif (is_dir($file)) foreach (glob($file.'/*') ?: [] as $child) @unlink($child);
            if (is_dir($file)) @rmdir($file);
        }
        @rmdir($this->base);
        parent::tearDown();
    }

    private function snapshot(): string { return $this->base.'/published.json'; }
    private function manifest(): string { return $this->base.'/snapshot-manifest.json'; }
    private function publicationRun(): MuseumPublicationRun
    {
        return MuseumPublicationRun::create(['status' => 'running']);
    }

    private function check(MuseumPublicationRun $run): void
    {
        app(MuseumExportContentVerifier::class)->verify(
            $run,$this->snapshot(),$this->manifest(),
            $this->base.'/media',$this->base.'/documents'
        );
    }

    private function changePayload(callable $mutation): void
    {
        $serializer = app(MuseumSnapshotSerializer::class);
        $data = json_decode(file_get_contents($this->snapshot()),true,512,JSON_THROW_ON_ERROR);
        $mutation($data);
        $raw = $serializer->encode($data);
        file_put_contents($this->snapshot(), $raw);
        $manifest = json_decode(file_get_contents($this->manifest()),true,512,JSON_THROW_ON_ERROR);
        $manifest['files']['published.json'] = [
            'sha256' => hash('sha256',$raw), 'bytes' => strlen($raw),
        ];
        $manifest['entry_count'] = count($data['entries']);
        file_put_contents($this->manifest(),$serializer->encode($manifest));
    }

    public function test_proof_binds_actual_exported_row_and_maybe_successful_run(): void
    {
        $run = $this->publicationRun();
        $this->check($run);
        $this->assertDatabaseCount('museum_export_content_proofs', 1);
        $row = MuseumExportContentProof::sole();
        $payload = json_decode(file_get_contents($this->snapshot()),true);
        $this->assertSame($this->entry->id,$row->subject_id);
        $this->assertSame('entry',$row->subject_kind);
        $this->assertSame(
            hash('sha256',app(MuseumSnapshotSerializer::class)->encode($payload['entries'][0])),
            $row->export_record_sha256);
        $this->assertSame(hash_file('sha256',$this->snapshot()),$row->snapshot_sha256);
        $this->assertSame(hash_file('sha256',$this->manifest()),$run->fresh()->manifest_sha256);
        $this->assertSame(1,$run->fresh()->content_proof_count);
        $this->assertNotNull($run->fresh()->content_verified_at);

        // Re-verification doesn't multiply proofs or change the immutable
        // meaning of one approved revision.
        $this->check($run);
        $this->assertDatabaseCount('museum_export_content_proofs', 1);
    }

    public function test_tampered_body_is_rejected_even_if_attacker_rehashes_manifest(): void
    {
        $this->changePayload(static function (&$data): void {
            $data['entries'][0]['body'] = '<p>Подменённый текст</p>';
        });
        $this->expectException(\RuntimeException::class);
        $this->expectExceptionMessage('Exported field does not match approved CMS source');
        try {
            $this->check($this->publicationRun());
        } finally {
            $this->assertDatabaseCount('museum_export_content_proofs', 0);
        }
    }

    public function test_unapproved_extra_entry_with_valid_new_digest_is_rejected(): void
    {
        $this->changePayload(static function (&$data): void {
            $extra = $data['entries'][0];
            $extra['slug'] = 'unapproved-extra-private';
            $data['entries'][] = $extra;
        });
        $this->expectException(\RuntimeException::class);
        $this->expectExceptionMessage('Approved subject count differs');
        try { $this->check($this->publicationRun()); }
        finally { $this->assertDatabaseCount('museum_export_content_proofs', 0); }
    }

    public function test_missing_approved_entry_is_rejected(): void
    {
        $this->changePayload(static function (&$data): void {$data['entries'] = [];});
        $this->expectException(\RuntimeException::class);
        $this->expectExceptionMessage('Approved subject count differs');
        try { $this->check($this->publicationRun()); }
        finally { $this->assertDatabaseCount('museum_export_content_proofs', 0); }
    }

    public function test_duplicate_approved_identity_is_rejected(): void
    {
        $this->changePayload(static function (&$data): void {
            $data['entries'][] = $data['entries'][0];
        });
        $this->expectException(\RuntimeException::class);
        $this->expectExceptionMessage('Duplicate exported content identity');
        try { $this->check($this->publicationRun()); }
        finally { $this->assertDatabaseCount('museum_export_content_proofs', 0); }
    }

    public function test_source_change_after_export_refuses_to_bind_stale_approval(): void
    {
        $this->entry->update(['body' => '<p>Другой новый текст</p>']);
        $this->expectException(\RuntimeException::class);
        $this->expectExceptionMessage('Exported field does not match approved CMS source');
        try { $this->check($this->publicationRun()); }
        finally { $this->assertDatabaseCount('museum_export_content_proofs', 0); }
    }

    public function test_fake_binary_reference_and_manifest_entry_do_not_create_proof(): void
    {
        $fake = str_repeat('a',64);
        $this->changePayload(static function (&$data) use ($fake): void {
            $data['entries'][0]['media'] = [['src'=>'/media/'.$fake.'.webp']];
        });
        $manifest = json_decode(file_get_contents($this->manifest()),true);
        $manifest['files']['media/'.$fake.'.webp'] = ['sha256'=>$fake,'bytes'=>200];
        file_put_contents($this->manifest(),app(MuseumSnapshotSerializer::class)->encode($manifest));
        $this->expectException(\RuntimeException::class);
        $this->expectExceptionMessage('Exported media metadata differs from approved CMS source');
        try { $this->check($this->publicationRun()); }
        finally { $this->assertDatabaseCount('museum_export_content_proofs', 0); }
    }

    public function test_approved_image_in_manifest_without_real_binary_fails_closed(): void
    {
        $digest = str_repeat('e',64);
        $image = \App\Models\MuseumMedia::create([
            'museum_entry_id'=>$this->entry->id,
            'storage_path'=>'museum/media/synthetic-not-real.webp',
            'sha256'=>$digest,
            'alt'=>'Тестовое изображение экспозиции с бумажной этикеткой',
            'caption'=>'Этикетка',
            'mime'=>'image/webp', 'width'=>60,'height'=>40,'size_bytes'=>200,
            'source_rights_pending'=>false,
        ]);
        // New exact approval of the entry AND the newly attached media,
        // distinct from the initial approval created in setUp.
        MuseumContentApproval::create([
            'museum_entry_id'=>$this->entry->id,'actor_id'=>1,
            'revision_sha256'=>MuseumApprovalRevision::fingerprint($this->entry->fresh()),
            'approved_at'=>now('UTC'),'dispatch_status'=>'queued',
        ]);
        $this->changePayload(static function (&$data) use ($digest): void {
            $data['entries'][0]['media'] = [[
                'src'=>'/media/'.$digest.'.webp',
                'alt'=>'Тестовое изображение экспозиции с бумажной этикеткой',
                'caption'=>'Этикетка','width'=>60,'height'=>40,
            ]];
        });
        $manifest = json_decode(file_get_contents($this->manifest()),true);
        $manifest['files']['media/'.$digest.'.webp'] = ['sha256'=>$digest,'bytes'=>200];
        file_put_contents($this->manifest(),app(MuseumSnapshotSerializer::class)->encode($manifest));

        $this->expectException(\RuntimeException::class);
        $this->expectExceptionMessage('Exported binary asset missing or mismatched manifest');
        try { $this->check($this->publicationRun()); }
        finally { $this->assertDatabaseCount('museum_export_content_proofs',0); }
    }

    public function test_precontract_legacy_export_never_claims_proof_without_required_approvals(): void
    {
        config(['museum.editorial_approval_queue'=>false]);
        $run = $this->publicationRun();
        $this->check($run);
        $this->assertDatabaseCount('museum_export_content_proofs',0);
        $this->assertNull($run->fresh()->content_verified_at);
        $this->assertNull($run->fresh()->content_proof_count);
    }

    public function test_manifest_hash_or_bytes_mismatch_fails_closed(): void
    {
        $manifest = json_decode(file_get_contents($this->manifest()),true);
        $manifest['files']['published.json']['sha256'] = str_repeat('1',64);
        file_put_contents($this->manifest(),app(MuseumSnapshotSerializer::class)->encode($manifest));
        $this->expectException(\RuntimeException::class);
        $this->expectExceptionMessage('Manifest does not bind actual snapshot bytes');
        try { $this->check($this->publicationRun()); }
        finally { $this->assertDatabaseCount('museum_export_content_proofs', 0); }
    }
}
