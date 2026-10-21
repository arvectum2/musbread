<?php

namespace App\Jobs;

use App\Models\MuseumPublicationRun;
use App\Models\MuseumExportContentProof;
use App\Support\MuseumExportContentVerifier;
use App\Support\MuseumVerifiedExportArchive;
use Illuminate\Contracts\Queue\ShouldQueue;
use Illuminate\Foundation\Queue\Queueable;
use Illuminate\Support\Facades\Artisan;
use Illuminate\Support\Facades\Cache;
use RuntimeException;
use Throwable;

final class PublishMuseumSnapshot implements ShouldQueue
{
    use Queueable;

    // Guard the lease: a queued export must time out well BEFORE its shared
    // cache lock expires. The retry_after must outlive BOTH job and lock, so
    // a dead worker cannot be redelivered while holding an expired lease.
    // Laravel enforces this per-job timeout even if a worker is launched with
    // a larger --timeout; timeout failure must never launch a late retry.
    public const JOB_TIMEOUT_SECONDS = 540;
    public const LOCK_TTL_SECONDS = 840;
    public const MIN_RETRY_AFTER_SECONDS = 900;
    public int $timeout = self::JOB_TIMEOUT_SECONDS;
    public bool $failOnTimeout = true;

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

        $lock = Cache::lock('museum:publication-export', self::LOCK_TTL_SECONDS);
        if (! $lock->get()) {
            throw new RuntimeException('Another publication is already in progress');
        }

        try {
            // A retry must never inherit a stale proof from a previously
            // interrupted or failed attempt, including if strict mode was
            // disabled between attempts. Completed runs return above.
            \Illuminate\Support\Facades\DB::transaction(static function () use ($run): void {
                MuseumExportContentProof::query()->where('publication_run_id', $run->id)->delete();
                $run->update([
                    'status' => 'running',
                    'attempts' => $run->attempts + 1,
                    'started_at' => now(),
                    'error_type' => null,
                    'snapshot_sha256' => null,
                    'content_verified_at' => null,
                    'content_proof_count' => null,
                    'manifest_sha256' => null,
                    'archive_id' => null,
                    'archive_receipt_sha256' => null,
                    'archive_file_count' => null,
                    'archived_at' => null,
                ]);
            });
            // Background publication must never bypass the same strict
            // content/link preflight that protects an operator-triggered
            // final export. The exporter checks BEFORE writing any files.
            // Warnings remain advisory; critical published-content errors
            // fail this run with only the safe exception class in the log.
            $parameters = ['--preflight-strict' => true];
            // Keep normal CMS scheduler/queue behavior backward compatible.
            // When an explicitly configured PRIVATE staging root exists, the
            // queued worker must not overwrite the tracked Next.js fixture or
            // static public webroot. The receiver reads only after SHA-256.
            $privateStage = config('museum.queued_export_staging_dir');
            if ($privateStage !== null && $privateStage !== '') {
                if (! is_string($privateStage) || ! str_starts_with($privateStage, '/')
                    || ! is_dir($privateStage) || is_link($privateStage)) {
                    throw new RuntimeException('Unsafe private queued export staging directory');
                }
                $resolvedStage = realpath($privateStage);
                $publicRoots = array_filter([
                    realpath(public_path()),
                    realpath(base_path('../web/public')),
                    realpath(base_path('../web/src')),
                ]);
                if ($resolvedStage === false || $resolvedStage === '/'
                    || array_any($publicRoots, static fn (string $root): bool =>
                        $resolvedStage === $root || str_starts_with($resolvedStage, $root.'/'))) {
                    throw new RuntimeException('Queued publication stage cannot be inside public or tracked web source');
                }
                $parameters['--output'] = rtrim($resolvedStage, '/').'/published.json';
                $parameters['--manifest'] = rtrim($privateStage, '/').'/snapshot-manifest.json';
                $parameters['--media-output-dir'] = rtrim($privateStage, '/').'/media';
                $parameters['--document-output-dir'] = rtrim($privateStage, '/').'/documents';
            }
            if ($this->outputPath !== null) $parameters['--output'] = $this->outputPath;
            if ($this->manifestPath !== null) $parameters['--manifest'] = $this->manifestPath;
            if ($this->mediaOutputDir !== null) $parameters['--media-output-dir'] = $this->mediaOutputDir;

            if (Artisan::call('museum:export', $parameters) !== 0) {
                throw new RuntimeException('museum:export returned a nonzero status');
            }

            $snapshot = $parameters['--output'] ?? base_path('../web/src/data/published.json');
            $manifest = $parameters['--manifest'] ?? base_path('../web/public/snapshot-manifest.json');
            $audit = json_decode(file_get_contents($manifest), true, flags: JSON_THROW_ON_ERROR);
            $hash = hash_file('sha256', $snapshot);
            if (($audit['files']['published.json']['sha256'] ?? '') !== $hash) {
                throw new RuntimeException('Publication snapshot checksum mismatch');
            }

            // In strict editorial-approval mode, a correct manifest digest is
            // necessary but not sufficient: establish which individually
            // approved CMS revisions actually appear in these exported bytes.
            // Fail closed on stale/missing/unapproved entries or assets.
            app(MuseumExportContentVerifier::class)->verify(
                $run, $snapshot, $manifest,
                $parameters['--media-output-dir'] ?? base_path('../web/public/media'),
                $parameters['--document-output-dir'] ?? base_path('../web/public/documents')
            );
            // Optional private archival AFTER independent per-object content
            // proof and BEFORE reporting success. Archive failures fail this
            // attempt closed, never claim a finished privately archived run.
            $archive = app(MuseumVerifiedExportArchive::class)->archive(
                $run->fresh(), $snapshot, $manifest,
                $parameters['--media-output-dir'] ?? base_path('../web/public/media'),
                $parameters['--document-output-dir'] ?? base_path('../web/public/documents')
            );
            $run->update([
                'status' => 'succeeded',
                'snapshot_sha256' => $hash,
                'finished_at' => now(),
                ...($archive === null ? [] : [
                    ...$archive,
                    'archived_at' => now('UTC'),
                ]),
            ]);
        } catch (Throwable $e) {
            // A package whose archive could not be finalized is NOT a
            // completed verified publication. Clear partially persisted
            // proof claims before failing this worker/retry.
            \Illuminate\Support\Facades\DB::transaction(static function () use ($run, $e): void {
                MuseumExportContentProof::query()->where('publication_run_id', $run->id)->delete();
                $run->update([
                    'status' => 'failed',
                    'error_type' => class_basename($e), // No raw paths or secrets.
                    'finished_at' => now(),
                    'content_verified_at' => null,
                    'content_proof_count' => null,
                    'manifest_sha256' => null,
                    'snapshot_sha256' => null,
                    'archive_id' => null,
                    'archive_receipt_sha256' => null,
                    'archive_file_count' => null,
                    'archived_at' => null,
                ]);
            });
            throw $e;
        } finally {
            $lock->release();
        }
    }
}
