<?php

namespace Tests\Feature;

use App\Jobs\PublishMuseumSnapshot;
use App\Models\MuseumEntry;
use App\Models\MuseumPublicationRun;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Cache;
use Illuminate\Support\Facades\Queue;
use Tests\TestCase;

class MuseumPublicationQueueTest extends TestCase
{
    use RefreshDatabase;

    public function test_scheduler_command_queues_a_single_auditable_job(): void
    {
        Queue::fake();

        $this->artisan('museum:queue-export')->assertSuccessful();
        $this->artisan('museum:queue-export')->assertSuccessful();

        Queue::assertPushed(PublishMuseumSnapshot::class, 1);
        $this->assertSame(1, MuseumPublicationRun::count());
        $this->assertSame('queued', MuseumPublicationRun::first()->status);
    }

    public function test_competing_worker_cannot_export_while_publication_lock_is_held(): void
    {
        // Real Laravel lock, not a mocked HTTP/UI claim. The rejected worker
        // must not increment its attempt count or overwrite the last version.
        MuseumEntry::create([
            'type' => 'news',
            'slug' => 'queue-lock-one',
            'title' => 'Одна одобренная запись',
            'body' => '<p>Только опубликованные данные</p>',
            'status' => 'published',
        ]);
        $run = MuseumPublicationRun::create(['status' => 'queued']);
        $root = storage_path('framework/testing/concurrent-queue-'.bin2hex(random_bytes(8)));
        mkdir($root, 0700, true);
        $output = $root.'/published.json';
        $manifest = $root.'/manifest.json';
        file_put_contents($output, "PRIOR_RELEASE_STILL_ACTIVE\n");
        file_put_contents($manifest, "PRIOR_MANIFEST_STILL_ACTIVE\n");
        $held = Cache::lock('museum:publication-export', 1200);
        $this->assertTrue($held->get());
        try {
            $job = new PublishMuseumSnapshot($run->id, $output, $manifest, $root.'/media');
            try {
                $job->handle();
                $this->fail('Concurrent publication worker acquired an occupied lock');
            } catch (\RuntimeException $error) {
                $this->assertStringContainsString('already in progress', $error->getMessage());
            }
            $this->assertSame('queued', $run->fresh()->status);
            $this->assertSame(0, $run->fresh()->attempts);
            $this->assertSame("PRIOR_RELEASE_STILL_ACTIVE\n", file_get_contents($output));
            $this->assertSame("PRIOR_MANIFEST_STILL_ACTIVE\n", file_get_contents($manifest));
            $this->assertDirectoryDoesNotExist($root.'/media');
        } finally {
            $held->release();
        }
        try {
            (new PublishMuseumSnapshot($run->id, $output, $manifest, $root.'/media'))->handle();
            $this->assertSame('succeeded', $run->fresh()->status);
            $this->assertSame(1, $run->fresh()->attempts);
            $this->assertSame(hash_file('sha256', $output), $run->fresh()->snapshot_sha256);
            // A duplicate queue delivery after success must be a no-op.
            (new PublishMuseumSnapshot($run->id, $output, $manifest, $root.'/media'))->handle();
            $this->assertSame(1, $run->fresh()->attempts);
        } finally {
            foreach (glob($root.'/*') ?: [] as $file) {
                if (is_dir($file)) @rmdir($file);
                else @unlink($file);
            }
            @rmdir($root);
        }
    }

    public function test_retry_wipes_old_inclusion_proofs_and_never_promotes_legacy_export_to_verified(): void
    {
        MuseumEntry::create([
            'type'=>'news','slug'=>'retry-proof-clear','title'=>'Синтетическая новость',
            'body'=>'<p>Новая версия без ручных одобрений</p>', 'status'=>'published',
        ]);
        $run = MuseumPublicationRun::create([
            'status'=>'failed',
            'attempts'=>1,
            'snapshot_sha256'=>str_repeat('e',64),
            'manifest_sha256'=>str_repeat('f',64),
            'content_verified_at'=>now('UTC'),
            'content_proof_count'=>1,
        ]);
        \App\Models\MuseumExportContentProof::create([
            'publication_run_id'=>$run->id,'approval_id'=>1,
            'subject_kind'=>'entry','subject_id'=>1,
            'revision_sha256'=>str_repeat('a',64),
            'snapshot_sha256'=>str_repeat('e',64),
            'export_record_sha256'=>str_repeat('b',64),
        ]);
        $dir=storage_path('framework/testing/proof-retry-'.bin2hex(random_bytes(6)));
        mkdir($dir,0700,true);
        try {
            (new PublishMuseumSnapshot($run->id, $dir.'/published.json',
                $dir.'/snapshot-manifest.json',$dir.'/media'))->handle();
            $run->refresh();
            $this->assertSame('succeeded',$run->status);
            $this->assertSame(2,$run->attempts);
            $this->assertNull($run->content_verified_at);
            $this->assertNull($run->content_proof_count);
            $this->assertNull($run->manifest_sha256);
            $this->assertDatabaseCount('museum_export_content_proofs',0);
        } finally {
            foreach (glob($dir.'/*') ?: [] as $file) {
                if (is_file($file)) @unlink($file);
                elseif (is_dir($file)) {
                    foreach (glob($file.'/*') ?: [] as $nested) @unlink($nested);
                    @rmdir($file);
                }
            }
            @rmdir($dir);
        }
    }

    public function test_job_exports_and_verifies_an_integrity_manifest(): void
    {
        $entry = MuseumEntry::create([
            'type' => 'news', 'slug' => 'queue-news', 'title' => 'Новость в очереди',
            'body' => 'Только проверенные публикации', 'status' => 'published',
        ]);

        $run = MuseumPublicationRun::create(['status' => 'queued']);
        $base = storage_path('framework/testing/job-'.uniqid());
        mkdir($base, 0700, true);
        $output = $base.'/published.json';
        $manifest = $base.'/manifest.json';

        try {
            $job = new PublishMuseumSnapshot($run->id, $output, $manifest, $base.'/media');
            $job->handle();
            $run->refresh();
            $this->assertSame('succeeded', $run->status);
            $this->assertSame(1, $run->attempts);
            $this->assertNull($run->content_verified_at);
            $this->assertNull($run->content_proof_count);
            $this->assertDatabaseCount('museum_export_content_proofs', 0);
            $this->assertNotNull($run->started_at);
            $this->assertNotNull($run->finished_at);
            $this->assertSame(hash_file('sha256', $output), $run->snapshot_sha256);
            $this->assertSame('queue-news', json_decode(file_get_contents($output), true)['entries'][0]['slug']);

            $job->handle();
            $this->assertSame(1, $run->fresh()->attempts);
        } finally {
            foreach (glob($base.'/*') ?: [] as $path) {
                if (is_dir($path)) @rmdir($path);
                else @unlink($path);
            }
            @rmdir($base);
        }
    }

    public function test_background_queue_refuses_invalid_published_links_without_changing_release_files(): void
    {
        // This content is editorially approved but references a missing
        // public page: a high-risk core publishing condition. A scheduled
        // queue must apply the SAME strict preflight as manual release.
        $entry = MuseumEntry::create([
            'type' => 'news', 'slug' => 'queued-invalid-link',
            'title' => 'Новость со сломанной ссылкой',
            'body' => '<p>Текст <a href="/news/not-a-public-page/">несуществующая новость</a></p>',
            'status' => 'published',
        ]);
        $run = MuseumPublicationRun::create(['status' => 'queued']);
        $base = storage_path('framework/testing/strict-'.bin2hex(random_bytes(6)));
        mkdir($base, 0700, true);
        $output = $base.'/published.json';
        $manifest = $base.'/manifest.json';
        $media = $base.'/media';
        // Existing release must remain bit-identical on failed preflight.
        file_put_contents($output, "UNCHANGED_PUBLIC_SNAPSHOT\n");
        file_put_contents($manifest, "UNCHANGED_PUBLIC_MANIFEST\n");
        try {
            try {
                (new PublishMuseumSnapshot($run->id, $output, $manifest, $media))->handle();
                $this->fail('Queue accepted a critical broken link in published content');
            } catch (\RuntimeException $e) {
                $this->assertStringContainsString('nonzero status', $e->getMessage());
            }
            $this->assertSame("UNCHANGED_PUBLIC_SNAPSHOT\n", file_get_contents($output));
            $this->assertSame("UNCHANGED_PUBLIC_MANIFEST\n", file_get_contents($manifest));
            $this->assertDirectoryDoesNotExist($media);
            $this->assertSame('failed', $run->fresh()->status);
            $this->assertSame(1, $run->fresh()->attempts);
            $this->assertSame('RuntimeException', $run->fresh()->error_type);
            $this->assertNull($run->fresh()->snapshot_sha256);

            // After an editor corrects the source content, a fresh queued
            // attempt must be able to publish normally.
            $entry->update(['body' => '<p>Проверенная новость без битых внутренних ссылок.</p>']);
            $retry = new PublishMuseumSnapshot($run->id, $output, $manifest, $media);
            $retry->handle();
            $this->assertSame('succeeded', $run->fresh()->status);
            $this->assertSame(2, $run->fresh()->attempts);
            $this->assertNotSame("UNCHANGED_PUBLIC_SNAPSHOT\n", file_get_contents($output));
            $this->assertSame(
                hash_file('sha256',$output),
                json_decode(file_get_contents($manifest),true)['files']['published.json']['sha256']
            );
        } finally {
            foreach (glob($base.'/*') ?: [] as $path) {
                if (is_dir($path)) @rmdir($path); else @unlink($path);
            }
            @rmdir($base);
        }
    }

    public function test_background_worker_refuses_unapproved_entry_in_strict_opt_in_mode(): void
    {
        config([
            'museum.editorial_approval_queue' => true,
            'museum.queue_publication' => true,
            'queue.default' => 'database',
            'cache.default' => 'database',
        ]);
        MuseumEntry::create([
            'type' => 'news', 'slug' => 'not-explicitly-approved',
            'title' => 'Черновик публикации с флагом', 'body' => '<p>Тест</p>',
            'status' => 'published',
        ]);
        $run = MuseumPublicationRun::create(['status' => 'queued']);
        $base = storage_path('framework/testing/job-explicit-approval');
        if (! is_dir($base)) mkdir($base, 0700, true);
        $output = $base.'/published.json';
        $manifest = $base.'/manifest.json';
        file_put_contents($output, 'LAST_VALID_RELEASE');
        try {
            try {
                (new PublishMuseumSnapshot($run->id, $output, $manifest, $base.'/media'))->handle();
                $this->fail('Worker ignored strict editorial approval gate');
            } catch (\RuntimeException $e) {
                $this->assertStringContainsString('nonzero status', $e->getMessage());
            }
            $this->assertSame('LAST_VALID_RELEASE', file_get_contents($output));
            $this->assertFileDoesNotExist($manifest);
            $this->assertSame('failed', $run->fresh()->status);
            $this->assertNull($run->fresh()->snapshot_sha256);
        } finally {
            @unlink($output);
            @unlink($manifest);
        }
    }

    public function test_publication_journal_is_admin_only_and_immutable_from_ui(): void
    {
        $role = \MoonShine\Laravel\Models\MoonshineUserRole::where('name', 'Editor')->firstOrFail();
        $editor = \MoonShine\Laravel\Models\MoonshineUser::factory()
            ->create(['moonshine_user_role_id' => $role->id]);
        $this->actingAs($editor, 'moonshine')
            ->get('/admin/resource/museum-publication-run-resource/museum-publication-run-index-page')
            ->assertForbidden();

        $admin = \MoonShine\Laravel\Models\MoonshineUser::factory()->create();
        $this->actingAs($admin, 'moonshine')
            ->get('/admin/resource/museum-publication-run-resource/museum-publication-run-index-page')
            ->assertOk();
        $this->post('/admin/resource/museum-publication-run-resource/crud', [
            'status' => 'succeeded',
        ])->assertForbidden();
        $this->assertSame(0, MuseumPublicationRun::count());
    }

    public function test_job_failure_records_only_the_exception_type(): void
    {
        $run = MuseumPublicationRun::create(['status' => 'queued']);
        $job = new PublishMuseumSnapshot($run->id,
            '/this/path/does/not/exist/out.json',
            '/this/path/does/not/exist/manifest.json',
            '/this/path/does/not/exist/media');
        try {
            $job->handle();
            $this->fail('Expected publication failure');
        } catch (\Throwable $e) {
            $this->assertSame('failed', $run->fresh()->status);
            $this->assertNotNull($run->fresh()->error_type);
            $this->assertStringNotContainsString('/this/path', $run->fresh()->error_type);
        }
    }
}
