<?php

declare(strict_types=1);

namespace App\Http\Controllers;

use App\Models\MuseumEntry;
use App\Support\MuseumApprovalRevision;
use App\Support\MuseumContentPreflight;
use App\Support\MuseumSectionAccess;
use Illuminate\Http\Response;

/** Authenticated read-only editor checklist; no publication action is exposed. */
final class MuseumContentPreflightController extends Controller
{
    public function index(MuseumContentPreflight $service): Response
    {
        $actor = MuseumSectionAccess::user();
        if ($actor === null) abort(403);

        $report = $service->report($actor);
        $durableQueue = (bool) config('museum.queue_publication', false)
            && in_array(config('queue.default'), ['database', 'redis'], true)
            && in_array(config('cache.default'), ['database', 'redis'], true);
        $mayApprove = $actor->isSuperUser() && $durableQueue
            && (bool) config('museum.editorial_approval_queue', false)
            && $report['errors'] === 0;
        $revisionChecksums = [];
        if ($mayApprove) {
            $eligible = collect($report['records'])
                ->filter(static fn ($row) => $row['state'] === 'ready' && $row['error_count'] === 0)
                ->pluck('id')->all();
            foreach (MuseumEntry::query()->whereIn('id', $eligible)->get() as $entry) {
                $revisionChecksums[$entry->id] = MuseumApprovalRevision::fingerprint($entry);
            }
        }

        return response()->view('entries.preflight', [
            'report' => $report,
            'mayApprove' => $mayApprove,
            'revisionChecksums' => $revisionChecksums,
            'mayRequestExport' => $actor->isSuperUser(),
            'exportQueueConfigured' => $durableQueue,
        ], 200, [
            'Cache-Control' => 'private, no-store, max-age=0',
            'Pragma' => 'no-cache',
            'X-Robots-Tag' => 'noindex, nofollow, noarchive',
            'X-Content-Type-Options' => 'nosniff',
            'X-Frame-Options' => 'DENY',
            'Referrer-Policy' => 'no-referrer',
            'Content-Security-Policy' => "default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'",
        ]);
    }
}
