<?php

namespace App\Console\Commands;

use App\Jobs\PublishMuseumSnapshot;
use App\Models\MuseumPublicationRun;
use Illuminate\Console\Command;
use Illuminate\Support\Facades\Cache;

final class QueueMuseumPublication extends Command
{
    protected $signature = 'museum:queue-export';
    protected $description = 'Enqueue one auditable museum snapshot publication (needs a queue worker)';

    public function handle(): int
    {
        // Serialize the check-and-enqueue operation; two hourly/manual requests
        // must not create two pending jobs concurrently.
        $lock = Cache::lock('museum:publication-enqueue', 30);
        if (! $lock->get()) {
            $this->warn('Another publication request is being enqueued');
            return self::FAILURE;
        }

        try {
            if (MuseumPublicationRun::query()->whereIn('status', ['queued', 'running'])->exists()) {
                $this->warn('A publication request is already queued or running');
                return self::SUCCESS;
            }

            $run = MuseumPublicationRun::create(['status' => 'queued']);
            try {
                PublishMuseumSnapshot::dispatch($run->id);
            } catch (\Throwable $exception) {
                $run->update([
                    'status' => 'failed',
                    'error_type' => class_basename($exception),
                    'finished_at' => now(),
                ]);
                throw $exception;
            }
            $this->info("Queued museum publication #{$run->id} on museum-publish");
            return self::SUCCESS;
        } finally {
            $lock->release();
        }
    }
}
