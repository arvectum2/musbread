<?php

namespace Tests\Feature;

use App\Models\MuseumContentApproval;
use App\Models\MuseumEntry;
use App\Models\MuseumEvent;
use App\Models\MuseumPublicationRun;
use App\Support\MuseumApprovalRevision;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Artisan;
use Illuminate\Support\Facades\DB;
use MoonShine\Laravel\Models\MoonshineUser;
use Tests\TestCase;

/** Genuine protected editorial POSTs and the real database queue worker.
 *  Tests are disposable; never touch production SQLite or Next fixture.
 */
final class MuseumRealApprovalToQueuedExportTest extends TestCase
{
    use RefreshDatabase;

    public function test_admin_approves_exact_revisions_then_real_worker_exports_private_snapshot_and_clock(): void
    {
        $export = getenv('MUSBREAD_APPROVAL_QA_OUTPUT_DIR');
        $external = is_string($export) && $export !== '';
        $base = $external ? $export : storage_path('framework/testing/approval-http-'.bin2hex(random_bytes(6)));
        if (! is_dir($base)) mkdir($base, 0700, true);
        config([
            'museum.editorial_approval_queue' => true,
            'museum.queue_publication' => true,
            'museum.queued_export_staging_dir' => $base,
            'queue.default' => 'database',
            'cache.default' => 'database',
        ]);
        $admin = MoonshineUser::factory()->create();
        $published = MuseumEntry::create([
            'type' => 'news', 'slug' => 'qa-approved-edition-queue-news',
            'title' => 'QA: Новость после настоящего решения редактора',
            'body' => '<p>Только эта проверенная редакция одобрена в локальном тесте.</p>',
            'status' => 'published',
        ]);
        $draft = MuseumEntry::create([
            'type' => 'news', 'slug' => 'qa-unapproved-draft-hidden',
            'title' => 'QA: Приватный черновик редактора',
            'body' => '<p>Запрещено на публичном сайте.</p>',
            'status' => 'draft',
        ]);
        $event = MuseumEvent::create([
            'slug' => 'qa-approved-queue-event', 'title' => 'QA: Одобренное событие',
            'category' => 'exhibition', 'starts_at' => '2026-10-19',
            'excerpt' => 'Только тестовая запись.', 'body' => 'Временное QA событие.',
            'status' => 'published',
        ]);
        try {
            $this->actingAs($admin, 'moonshine');
            $started = microtime(true);
            foreach ([
                [$published, 'museum.entries.approve-and-queue'],
                [$event, 'museum.events.approve-and-queue'],
            ] as [$subject, $route]) {
                $revision = MuseumApprovalRevision::forSubject($subject->fresh());
                $this->post(route($route, $subject), ['revision_sha256' => $revision])
                    ->assertRedirect(route('museum.content.preflight'));
            }
            $approvals = MuseumContentApproval::query()->orderBy('id')->get();
            $this->assertCount(2, $approvals);
            $this->assertSame(1, MuseumPublicationRun::count());
            $this->assertSame(1, DB::table('jobs')->count());
            foreach ($approvals as $approval) {
                $this->assertSame('queued', $approval->dispatch_status);
                $this->assertNotNull($approval->approved_at);
                $this->assertNotNull($approval->publication_run_id);
                $this->assertSame(MuseumPublicationRun::sole()->id, $approval->publication_run_id);
            }
            $this->assertNull($draft->fresh()->published_at);
            // This invokes the REAL Laravel queue:work implementation,
            // not Queue::fake, sync dispatch or direct ->handle() of a job.
            $result = Artisan::call('queue:work', [
                'connection' => 'database', '--queue' => 'museum-publish',
                '--once' => true, '--tries' => 1, '--timeout' => 90,
            ]);
            $this->assertSame(0, $result, Artisan::output());
            $run = MuseumPublicationRun::sole();
            $this->assertSame('succeeded', $run->status);
            $this->assertSame(1, $run->attempts);
            $this->assertSame(0, DB::table('jobs')->count());
            $this->assertSame(0, DB::table('failed_jobs')->count());
            $snapshot = $base.'/published.json';
            $manifest = $base.'/snapshot-manifest.json';
            $this->assertFileExists($snapshot);
            $this->assertFileExists($manifest);
            $content = json_decode(file_get_contents($snapshot), true, flags: JSON_THROW_ON_ERROR);
            $signed = json_decode(file_get_contents($manifest), true, flags: JSON_THROW_ON_ERROR);
            $this->assertSame(['qa-approved-edition-queue-news'], array_column($content['entries'], 'slug'));
            $this->assertSame(['qa-approved-queue-event'], array_column($content['events'], 'slug'));
            $sha = hash_file('sha256', $snapshot);
            $this->assertSame($sha, $signed['files']['published.json']['sha256']);
            $this->assertSame($sha, $run->snapshot_sha256);
            $this->assertSame(2, $run->content_proof_count);
            $this->assertNotNull($run->content_verified_at);
            $this->assertSame(hash_file('sha256', $manifest), $run->manifest_sha256);
            $this->assertDatabaseCount('museum_export_content_proofs', 2);
            $this->assertSame(['entry', 'event'], \App\Models\MuseumExportContentProof::query()
                ->orderBy('subject_kind')->pluck('subject_kind')->all());
            $this->get(route('museum.content.approval-journal'))->assertOk()
                ->assertSee('Подтверждено в проверенном пакете')
                ->assertSee('Подтверждено 2 одобренных объектов');
            $lastApproval = $approvals->max(static fn ($item) => $item->approved_at->getTimestamp());
            $elapsedAtExport = microtime(true) - $lastApproval;
            $this->assertTrue($elapsedAtExport >= 0);
            $this->assertLessThan(3600, $elapsedAtExport);
            if ($external) {
                file_put_contents($base.'/approval-observation.json', json_encode([
                    'approved_at_utc' => $approvals->last()->approved_at->toIso8601String(),
                    'approval_unix_seconds' => $lastApproval,
                    'approval_clock_start_unix' => $started,
                    'approval_to_export_seconds' => $elapsedAtExport,
                    'run_status' => $run->status,
                    'snapshot_sha256' => $sha,
                    'approvals' => $approvals->count(),
                    'real_database_jobs_finished' => 1,
                ], JSON_PRETTY_PRINT | JSON_THROW_ON_ERROR));
            }
        } finally {
            if (! $external) {
                foreach (glob($base.'/*') ?: [] as $item) if (is_file($item)) unlink($item);
                @rmdir($base);
            }
        }
    }
}
