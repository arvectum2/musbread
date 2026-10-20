<?php

namespace Tests\Feature;

use App\Models\MuseumContentApproval;
use App\Models\MuseumEntry;
use App\Models\MuseumEvent;
use App\Models\MuseumMedia;
use App\Models\MuseumExportContentProof;
use App\Models\MuseumPublicationRun;
use App\Support\MuseumApprovalRevision;
use App\Support\MuseumExportContentVerifier;
use App\Support\MuseumSnapshotSerializer;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Artisan;
use Illuminate\Support\Facades\Storage;
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

    private function reexport(): void
    {
        $this->assertSame(0, Artisan::call('museum:export', [
            '--output'=>$this->snapshot(), '--manifest'=>$this->manifest(),
            '--media-output-dir'=>$this->base.'/media',
            '--document-output-dir'=>$this->base.'/documents',
        ]), Artisan::output());
    }

    private function approve($subject, string $kind): void
    {
        MuseumContentApproval::create([
            ['entry'=>'museum_entry_id', 'event'=>'museum_event_id'][$kind]=>$subject->id,
            'actor_id'=>1,
            'revision_sha256'=>MuseumApprovalRevision::forSubject($subject->fresh()),
            'dispatch_status'=>'queued',
            'approved_at'=>now('UTC'),
        ]);
    }

    /** Valid, approved bidirectional entry/event links in actual export bytes. */
    private function linkedGraph(): array
    {
        $other = MuseumEntry::create([
            'type'=>'news', 'slug'=>'also-public-news',
            'title'=>'Вторая одобренная новость',
            'body'=>'<p>Одобренная ссылка для проверки</p>',
            'status'=>'published',
        ]);
        $event = MuseumEvent::create([
            'slug'=>'verified-tour', 'title'=>'Афиша проверенного мероприятия',
            'category'=>'Экскурсия', 'starts_at'=>now()->addWeek()->toDateString(),
            'excerpt'=>'Программа экскурсии', 'body'=>'<p>Действующие тестовые даты</p>',
            'status'=>'published',
        ]);
        $this->entry->relatedEntries()->sync([$other->id]);
        $this->entry->linkedEvents()->sync([$event->id]);
        // The event uses the same pivot table in the opposite direction.
        $this->approve($this->entry, 'entry');
        $this->approve($other, 'entry');
        $this->approve($event, 'event');
        $this->reexport();
        return [$other,$event];
    }

    public function test_real_approved_content_graph_is_independently_verified(): void
    {
        $this->linkedGraph();
        $data = json_decode(file_get_contents($this->snapshot()),true);
        $source = collect($data['entries'])->firstWhere('slug', $this->entry->slug);
        $event = collect($data['events'])->firstWhere('slug', 'verified-tour');
        $this->assertSame('/news/also-public-news/', $source['related_entries'][0]['href']);
        $this->assertSame('/events/verified-tour/', $source['related_events'][0]['href']);
        $this->assertSame('/news/verified-museum-news/', $event['related_entries'][0]['href']);
        $run=$this->publicationRun();
        $this->check($run);
        $this->assertSame(3,$run->fresh()->content_proof_count);
        $this->assertDatabaseCount('museum_export_content_proofs',3);
    }

    public function test_rehashed_manifest_does_not_authorize_a_forged_related_entry_link(): void
    {
        $this->linkedGraph();
        $this->changePayload(static function (&$data): void {
            foreach ($data['entries'] as &$row) {
                if ($row['slug']==='verified-museum-news') {
                    $row['related_entries'][0]['href']='/news/unapproved-target/';
                }
            }
        });
        $this->expectException(\RuntimeException::class);
        $this->expectExceptionMessage('Exported related entry links differ');
        try { $this->check($this->publicationRun()); }
        finally { $this->assertDatabaseCount('museum_export_content_proofs',0); }
    }

    public function test_rehashed_manifest_does_not_authorize_a_forged_related_event_link(): void
    {
        $this->linkedGraph();
        $this->changePayload(static function (&$data): void {
            foreach ($data['entries'] as &$row) {
                if ($row['slug']==='verified-museum-news') {
                    $row['related_events'][0]['title']='Другое неодобренное событие';
                }
            }
        });
        $this->expectException(\RuntimeException::class);
        $this->expectExceptionMessage('Exported related event links differ');
        try { $this->check($this->publicationRun()); }
        finally { $this->assertDatabaseCount('museum_export_content_proofs',0); }
    }

    public function test_rehashed_manifest_does_not_authorize_a_forged_event_related_entry(): void
    {
        $this->linkedGraph();
        $this->changePayload(static function (&$data): void {
            $data['events'][0]['related_entries'][0]['title']='Совершенно чужой материал';
        });
        $this->expectException(\RuntimeException::class);
        $this->expectExceptionMessage('Exported event related links differ');
        try { $this->check($this->publicationRun()); }
        finally { $this->assertDatabaseCount('museum_export_content_proofs',0); }
    }

    public function test_forbidden_public_schema_extra_fields_fail_even_with_rehashed_manifest(): void
    {
        $this->changePayload(static function (&$data): void {
            $data['entries'][0]['editor_email']='not-allowed@example.invalid';
        });
        $this->expectException(\RuntimeException::class);
        $this->expectExceptionMessage('Export contains unexpected public-schema fields');
        try { $this->check($this->publicationRun()); }
        finally { $this->assertDatabaseCount('museum_export_content_proofs',0); }
    }

    public function test_unknown_top_level_data_cannot_be_injected_with_valid_manifest_hash(): void
    {
        $this->changePayload(static function (&$data): void {
            $data['staff_contacts'] = [['email'=>'secret@example.invalid']];
        });
        $this->expectException(\RuntimeException::class);
        $this->expectExceptionMessage('Export contains unapproved top-level site data');
        try { $this->check($this->publicationRun()); }
        finally { $this->assertDatabaseCount('museum_export_content_proofs',0); }
    }

    public function test_rehashed_site_description_must_still_match_trusted_static_identity(): void
    {
        $this->changePayload(static function (&$data): void {
            $data['site']['description']='Подменённый текст для сайта';
        });
        $this->expectException(\RuntimeException::class);
        $this->expectExceptionMessage('Export contains unapproved top-level site data');
        try { $this->check($this->publicationRun()); }
        finally { $this->assertDatabaseCount('museum_export_content_proofs',0); }
    }

    public function test_valid_approved_event_cover_and_attacked_alt_are_distinguished(): void
    {
        Storage::fake('local');
        $image=imagecreatetruecolor(12,10);
        try {
            ob_start();
            imagewebp($image);
            $bytes=ob_get_clean();
        } finally {
            imagedestroy($image);
        }
        $this->assertIsString($bytes);
        $digest=hash('sha256',$bytes);
        Storage::disk('local')->put('museum/media/approval-proof.webp',$bytes);
        $media=MuseumMedia::create([
            'museum_entry_id'=>$this->entry->id,
            'storage_path'=>'museum/media/approval-proof.webp',
            'sha256'=>$digest,
            'alt'=>'Историческая хлебная печь и подробная музейная подпись к экспонату',
            'caption'=>'Печь в зале', 'long_description'=>'Подробное описание печи',
            'mime'=>'image/webp','width'=>12,'height'=>10,
            'size_bytes'=>strlen($bytes), 'source_rights_pending'=>false,
        ]);
        $event=MuseumEvent::create([
            'slug'=>'verified-cover-event','title'=>'Афиша с одобренной обложкой',
            'category'=>'Экскурсия','starts_at'=>now()->addWeek()->toDateString(),
            'excerpt'=>'Экскурсия с обложкой','body'=>'<p>Тестовая экскурсия</p>',
            'status'=>'published','cover_media_id'=>$media->id,
        ]);
        $this->approve($this->entry,'entry');
        $this->approve($event,'event');
        $this->reexport();
        $data=json_decode(file_get_contents($this->snapshot()),true);
        $this->assertSame('/media/'.$digest.'.webp',$data['events'][0]['cover_image']['src']);
        $run=$this->publicationRun();
        $this->check($run);
        $this->assertSame(2,$run->fresh()->content_proof_count);
        // Now alter the supposedly approved event alt. Rehash BOTH JSON and
        // its manifest; the independent CMS model still denies this proof.
        $this->changePayload(static function (&$data):void {
            $data['events'][0]['cover_image']['alt']='Подменённая подпись';
        });
        $this->expectException(\RuntimeException::class);
        $this->expectExceptionMessage('Exported event cover differs from approved CMS source');
        try { $this->check($this->publicationRun()); }
        finally { $this->assertDatabaseCount('museum_export_content_proofs',2); }
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
