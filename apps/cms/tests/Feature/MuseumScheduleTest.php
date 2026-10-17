<?php

namespace Tests\Feature;

use Illuminate\Console\Scheduling\Schedule;
use Tests\TestCase;

class MuseumScheduleTest extends TestCase
{
    public function test_museum_export_is_scheduled_hourly_without_overlap(): void
    {
        $tasks = collect(app(Schedule::class)->events())
            ->filter(fn ($event) => str_contains($event->command ?? '', 'museum:export'));

        $this->assertCount(1, $tasks);
        $event = $tasks->first();
        $this->assertSame('0 * * * *', $event->expression);
        // This hourly direct scheduler is normally enabled while the
        // private queue-worker has not been approved for production.
        $this->assertStringContainsString('--preflight-strict', $event->command);
        $this->assertTrue($event->withoutOverlapping);
    }
}
