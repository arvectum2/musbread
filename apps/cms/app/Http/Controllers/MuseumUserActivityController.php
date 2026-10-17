<?php

declare(strict_types=1);

namespace App\Http\Controllers;

use App\Models\MuseumAuditRecord;
use App\Models\MuseumPublicationRun;
use App\Models\MuseumEntry;
use App\Models\MuseumEvent;
use App\Models\MuseumSection;
use App\Support\MuseumEntryPublicationState;
use Illuminate\Support\Carbon;
use App\Support\MuseumSectionAccess;
use Illuminate\Http\Request;
use Illuminate\Http\Response;

/** TZ-236: read-only operational statistics, never exposed to public static web. */
final class MuseumUserActivityController extends Controller
{
    public function index(Request $request): Response
    {
        $user = MuseumSectionAccess::user();
        if ($user === null || ! $user->isSuperUser()) abort(403);
        $input = $request->validate([
            'from' => ['nullable', 'date_format:Y-m-d'],
            'to' => ['nullable', 'date_format:Y-m-d'],
            'actor_id' => ['nullable', 'integer', 'min:1'],
        ]);
        $from = isset($input['from']) ? Carbon::createFromFormat('!Y-m-d', $input['from'])->startOfDay()
            : now()->subDays(30)->startOfDay();
        $to = isset($input['to']) ? Carbon::createFromFormat('!Y-m-d', $input['to'])->startOfDay()
            : today();
        if ($from->lessThan(today()->subYears(2)) || $from->greaterThan($to)
            || $to->greaterThan(today()->addDay())) {
            abort(422, 'Неверный период: начало не позже окончания, не более двух лет назад и не позже завтрашнего дня');
        }
        $endExclusive = $to->copy()->addDay();
        $actorId = isset($input['actor_id']) ? (int)$input['actor_id'] : null;
        $query = MuseumAuditRecord::query()->where('created_at', '>=', $from)
            ->where('created_at', '<', $endExclusive);
        if ($actorId !== null) $query->where('actor_id', $actorId);
        $total = (clone $query)->count();
        $uniqueActors = (clone $query)->whereNotNull('actor_id')->distinct()->count('actor_id');
        $actions = (clone $query)->selectRaw('action, COUNT(*) AS total')->groupBy('action')->orderBy('action')->pluck('total', 'action');
        $subjects = (clone $query)->selectRaw('subject_type, COUNT(*) AS total')->groupBy('subject_type')->orderByDesc('total')->orderBy('subject_type')->pluck('total', 'subject_type');
        $users = (clone $query)->whereNotNull('actor_id')->selectRaw('actor_id, COUNT(*) AS total')
            ->groupBy('actor_id')->orderByDesc('total')->orderBy('actor_id')->limit(50)->get();
        // DATE() is available on SQLite, MariaDB/MySQL and PostgreSQL. Aggregate
        // in SQL so a two-year audit window never loads every private row.
        $daily = (clone $query)->selectRaw('DATE(created_at) AS day, COUNT(*) AS total')
            ->groupByRaw('DATE(created_at)')->orderBy('day')->get();
        $recent = (clone $query)->orderByDesc('created_at')->orderByDesc('id')->limit(100)->get();

        // Publications are system-wide queue runs, not attributed to any
        // employee. Keep them distinct from the actor/date-filtered audit.
        $publicationStatuses = MuseumPublicationRun::query()
            ->selectRaw('status, COUNT(*) AS total')
            ->groupBy('status')->orderBy('status')->pluck('total', 'status');
        $recentPublications = MuseumPublicationRun::query()
            ->orderByDesc('id')->limit(20)->get();
        $approvedIds = MuseumEntryPublicationState::publishedSectionIds();
        $eligibleEvents = MuseumEvent::query()->public()
            ->where(static fn ($query) => $query->whereNull('museum_section_id')
                ->when($approvedIds !== [],
                    static fn ($query) => $query->orWhereIn('museum_section_id', $approvedIds)));
        $inventory = [
            'entry_drafts' => MuseumEntry::query()->where('status', 'draft')->count(),
            'entry_ready' => MuseumEntryPublicationState::apply(MuseumEntry::query(), 'ready')->count(),
            'entry_scheduled' => MuseumEntryPublicationState::apply(MuseumEntry::query(), 'scheduled')->count(),
            'entry_expired' => MuseumEntryPublicationState::apply(MuseumEntry::query(), 'expired')->count(),
            'event_drafts' => MuseumEvent::query()->where('status', 'draft')->count(),
            'event_ready' => $eligibleEvents->count(),
            'event_scheduled' => MuseumEvent::query()->where('status', 'published')
                ->where(static fn ($query) => $query->whereNull('published_at')
                    ->orWhere('published_at', '>', now()))
                ->where(static fn ($query) => $query->whereNull('unpublish_at')
                    ->orWhere('unpublish_at', '>', now()))->count(),
            'event_expired' => MuseumEvent::query()->where('status', 'published')
                ->whereNotNull('unpublish_at')->where('unpublish_at', '<=', now())->count(),
            'sections_draft' => MuseumSection::query()->where('status', 'draft')->count(),
            'sections_published' => MuseumSection::query()->where('status', 'published')->count(),
        ];

        return response()->view('entries.activity-stats', compact(
            'total', 'uniqueActors', 'actions', 'subjects', 'users', 'recent',
            'from', 'to', 'actorId', 'daily', 'publicationStatuses', 'recentPublications', 'inventory'
        ),200,[
            'Cache-Control' => 'private, no-store, max-age=0',
            'Pragma' => 'no-cache', 'X-Robots-Tag' => 'noindex, nofollow, noarchive',
            'X-Content-Type-Options' => 'nosniff', 'X-Frame-Options' => 'DENY',
            'Referrer-Policy' => 'no-referrer',
            'Content-Security-Policy' => "default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'",
        ]);
    }
}
