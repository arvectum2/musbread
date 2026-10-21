<?php

namespace App\Console\Commands;

use App\Models\MuseumPublicationRun;
use App\Jobs\PublishMuseumSnapshot;
use Illuminate\Console\Command;
use Illuminate\Support\Facades\Cache;

final class RecoverStalePublications extends Command
{
    protected $signature = 'museum:recover-stale-publications
        {--queued-minutes=120 : Age threshold for missing queue workers}
        {--running-minutes=45 : Age threshold for interrupted workers}';

    protected $description = 'Abandon timed-out requests so a future publication can proceed';

    public function handle(): int
    {
        $queued = filter_var($this->option('queued-minutes'), FILTER_VALIDATE_INT);
        $running = filter_var($this->option('running-minutes'), FILTER_VALIDATE_INT);
        if ($queued === false || $queued < 60 || $running === false || $running < 30) {
            $this->error('Queued threshold >=60 minutes and running threshold >=30 minutes are required');
            return self::FAILURE;
        }

        // Must not alter status while a legitimate exporter holds its lock.
        $lock = Cache::lock('museum:publication-export', PublishMuseumSnapshot::LOCK_TTL_SECONDS);
        if (! $lock->get()) {
            $this->info('Publisher is active; skipping stale-run recovery');
            return self::SUCCESS;
        }

        try {
            $staleIds = MuseumPublicationRun::query()
                ->where(static function ($query) use ($queued, $running): void {
                    $query->where(static function ($q) use ($queued): void {
                        $q->where('status', 'queued')
                            ->where('created_at', '<=', now()->subMinutes($queued));
                    })->orWhere(static function ($q) use ($running): void {
                        $q->where('status', 'running')
                            ->where('started_at', '<=', now()->subMinutes($running));
                    });
                })
                ->pluck('id');

            if ($staleIds->isEmpty()) {
                $this->info('No stale publication requests');
                return self::SUCCESS;
            }

            // 'abandoned' is terminal: a delayed old job must never replay it.
            $count = MuseumPublicationRun::query()
                ->whereIn('id', $staleIds)
                ->whereIn('status', ['queued', 'running'])
                ->update([
                    'status' => 'abandoned',
                    'error_type' => 'StalePublication',
                    'finished_at' => now(),
                ]);

            $this->info("Abandoned {$count} stale publication request(s)");
            return self::SUCCESS;
        } finally {
            $lock->release();
        }
    }
}
