<?php

declare(strict_types=1);

namespace App\Http\Controllers;

use App\Models\MuseumEntry;
use App\Models\MuseumEvent;
use App\Models\MuseumSection;
use App\Support\MuseumEntryPublicationState;
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
        $eventChecksums = [];
        $sectionChecksums = [];
        if ($mayApprove) {
            $eligible = collect($report['records'])
                ->filter(static fn ($row) => $row['state'] === 'ready' && $row['error_count'] === 0)
                ->pluck('id')->all();
            foreach (MuseumEntry::query()->whereIn('id', $eligible)->get() as $entry) {
                $revisionChecksums[$entry->id] = MuseumApprovalRevision::fingerprint($entry);
            }
            $eligibleEvents = collect($report['events'])
                ->filter(static fn ($row) => $row['state'] === 'ready' && $row['error_count'] === 0)
                ->pluck('id')->all();
            foreach (MuseumEvent::query()->whereIn('id', $eligibleEvents)->get() as $event) {
                $eventChecksums[$event->id] = MuseumApprovalRevision::forSubject($event);
            }
            $approvedSectionIds = MuseumEntryPublicationState::publishedSectionIds();
            foreach (MuseumSection::query()->whereIn('id', $approvedSectionIds)->get() as $section) {
                if (trim((string) $section->title) !== '') {
                    $sectionChecksums[$section->id] = MuseumApprovalRevision::forSubject($section);
                }
            }
        }

        $sections = $actor->isSuperUser()
            ? MuseumSection::query()->orderBy('sort_order')->orderBy('id')->get()
            : collect();

        return response()->view('entries.preflight', [
            'report' => $report,
            'mayApprove' => $mayApprove,
            'revisionChecksums' => $revisionChecksums,
            'eventChecksums' => $eventChecksums,
            'sectionChecksums' => $sectionChecksums,
            'sections' => $sections,
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
