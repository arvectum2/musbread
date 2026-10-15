<?php

namespace App\Jobs;

use App\Models\MuseumPublicationRun;
use Illuminate\Contracts\Queue\ShouldQueue;
use Illuminate\Foundation\Queue\Queueable;
use Illuminate\Support\Facades\Artisan;
use Illuminate\Support\Facades\Cache;
use RuntimeException;
use Throwable;

final class PublishMuseumSnapshot implements ShouldQueue
{
    use Queueable;

    public int $tries = 3;
    public array $backoff = [30, 120];

    public function __construct(
        public readonly int $publicationRunId,
        public readonly ?string $outputPath = null,
        public readonly ?string $manifestPath = null,
        public readonly ?string $mediaOutputDir = null,
    ) {
        $this->onQueue('museum-publish');
    }

    public function handle(): void
    {
        $run = MuseumPublicationRun::findOrFail($this->publicationRunId);
        if (in_array($run->status, ['succeeded', 'abandoned'], true)) {
            return; // Idempotency: never re-export a completed request on retry.
        }

        $lock = Cache::lock('museum:publication-export', 1200);
        if (! $lock->get()) {
            throw new RuntimeException('Another publication is already in progress');
        }

        try {
            $run->update([
                'status' => 'running',
                'attempts' => $run->attempts + 1,
                'started_at' => now(),
                'error_type' => null,
            ]);
            $parameters = [];
            if ($this->outputPath !== null) $parameters['--output'] = $this->outputPath;
            if ($this->manifestPath !== null) $parameters['--manifest'] = $this->manifestPath;
            if ($this->mediaOutputDir !== null) $parameters['--media-output-dir'] = $this->mediaOutputDir;

            if (Artisan::call('museum:export', $parameters) !== 0) {
                throw new RuntimeException('museum:export returned a nonzero status');
            }

            $snapshot = $this->outputPath ?? base_path('../web/src/data/published.json');
            $manifest = $this->manifestPath ?? base_path('../web/public/snapshot-manifest.json');
            $audit = json_decode(file_get_contents($manifest), true, flags: JSON_THROW_ON_ERROR);
            $hash = hash_file('sha256', $snapshot);
            if (($audit['files']['published.json']['sha256'] ?? '') !== $hash) {
                throw new RuntimeException('Publication snapshot checksum mismatch');
            }

            $run->update([
                'status' => 'succeeded',
                'snapshot_sha256' => $hash,
                'finished_at' => now(),
            ]);
        } catch (Throwable $e) {
            $run->update([
                'status' => 'failed',
                'error_type' => class_basename($e), // No raw exceptions containing paths or secrets.
                'finished_at' => now(),
            ]);
            throw $e;
        } finally {
            $lock->release();
        }
    }
}
