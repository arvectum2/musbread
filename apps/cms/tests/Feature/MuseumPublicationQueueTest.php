<?php

namespace Tests\Feature;

use App\Jobs\PublishMuseumSnapshot;
use App\Models\MuseumEntry;
use App\Models\MuseumPublicationRun;
use Illuminate\Foundation\Testing\RefreshDatabase;
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
