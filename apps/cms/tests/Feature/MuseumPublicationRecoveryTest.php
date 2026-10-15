<?php

namespace Tests\Feature;

use App\Jobs\PublishMuseumSnapshot;
use App\Models\MuseumPublicationRun;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Cache;
use Illuminate\Support\Facades\Queue;
use Tests\TestCase;

class MuseumPublicationRecoveryTest extends TestCase
{
    use RefreshDatabase;

    public function test_expired_queue_and_worker_requests_are_abandoned(): void
    {
        $queued = MuseumPublicationRun::create(['status' => 'queued']);
        $queued->forceFill(['created_at' => now()->subHours(3)])->saveQuietly();

        $running = MuseumPublicationRun::create([
            'status' => 'running', 'started_at' => now()->subHour(),
        ]);
        $recent = MuseumPublicationRun::create([
            'status' => 'running', 'started_at' => now()->subMinutes(5),
        ]);

        $this->artisan('museum:recover-stale-publications')->assertSuccessful();
        $this->assertSame('abandoned', $queued->fresh()->status);
        $this->assertSame('abandoned', $running->fresh()->status);
        $this->assertSame('StalePublication', $running->fresh()->error_type);
        $this->assertNotNull($running->fresh()->finished_at);
        $this->assertSame('running', $recent->fresh()->status);
    }

    public function test_queued_old_job_is_ignored_after_abandonment(): void
    {
        $run = MuseumPublicationRun::create(['status' => 'abandoned']);
        // Would fail if executed because the requested snapshot directory is invalid.
        (new PublishMuseumSnapshot($run->id, '/invalid/path/out.json'))->handle();
        $this->assertSame(0, $run->fresh()->attempts);
        $this->assertSame('abandoned', $run->fresh()->status);
    }

    public function test_recovery_does_not_interrupt_active_export(): void
    {
        $run = MuseumPublicationRun::create([
            'status' => 'running', 'started_at' => now()->subHours(2),
        ]);
        $held = Cache::lock('museum:publication-export', 1200);
        $this->assertTrue($held->get());
        try {
            $this->artisan('museum:recover-stale-publications')->assertSuccessful();
            $this->assertSame('running', $run->fresh()->status);
        } finally {
            $held->release();
        }
    }

    public function test_recovery_thresholds_cannot_be_lowered_unsafely(): void
    {
        $this->artisan('museum:recover-stale-publications', [
            '--queued-minutes' => 1, '--running-minutes' => 1,
        ])->assertFailed();
    }

    public function test_enqueue_is_blocked_when_a_second_dispatch_is_in_progress(): void
    {
        Queue::fake();
        $lock = Cache::lock('museum:publication-enqueue', 30);
        $this->assertTrue($lock->get());
        try {
            $this->artisan('museum:queue-export')->assertFailed();
            $this->assertSame(0, MuseumPublicationRun::count());
            Queue::assertNothingPushed();
        } finally {
            $lock->release();
        }

        $this->artisan('museum:queue-export')->assertSuccessful();
        Queue::assertPushed(PublishMuseumSnapshot::class, 1);
    }

    public function test_next_request_may_be_enqueued_after_abandonment(): void
    {
        Queue::fake();
        MuseumPublicationRun::create(['status' => 'abandoned']);
        $this->artisan('museum:queue-export')->assertSuccessful();
        Queue::assertPushed(PublishMuseumSnapshot::class, 1);
        $this->assertSame(1, MuseumPublicationRun::where('status', 'queued')->count());
    }
}
