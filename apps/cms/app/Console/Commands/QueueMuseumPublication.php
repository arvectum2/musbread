<?php

namespace App\Console\Commands;

use App\Jobs\PublishMuseumSnapshot;
use App\Models\MuseumPublicationRun;
use Illuminate\Console\Command;

final class QueueMuseumPublication extends Command
{
    protected $signature = 'museum:queue-export';
    protected $description = 'Enqueue one auditable museum snapshot publication (needs a queue worker)';

    public function handle(): int
    {
        if (MuseumPublicationRun::query()->whereIn('status', ['queued', 'running'])->exists()) {
            $this->warn('A publication request is already queued or running');
            return self::SUCCESS;
        }

        $run = MuseumPublicationRun::create(['status' => 'queued']);
        PublishMuseumSnapshot::dispatch($run->id);
        $this->info("Queued museum publication #{$run->id} on museum-publish");
        return self::SUCCESS;
    }
}
