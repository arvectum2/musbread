<?php

declare(strict_types=1);

namespace App\Http\Controllers;

use App\Models\MuseumAuditRecord;
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
            'actor_id' => ['nullable', 'integer', 'min:1'],
        ]);
        $from = isset($input['from']) ? \Illuminate\Support\Carbon::createFromFormat('!Y-m-d', $input['from'])->startOfDay() : now()->subDays(30)->startOfDay();
        if ($from->lessThan(now()->subYears(2)) || $from->greaterThan(now()->addDay())) abort(422, 'Дата вне допустимого диапазона');
        $actorId = isset($input['actor_id']) ? (int)$input['actor_id'] : null;
        $query = MuseumAuditRecord::query()->where('created_at', '>=', $from);
        if ($actorId !== null) $query->where('actor_id', $actorId);
        $total = (clone $query)->count();
        $uniqueActors = (clone $query)->whereNotNull('actor_id')->distinct()->count('actor_id');
        $actions = (clone $query)->selectRaw('action, COUNT(*) AS total')->groupBy('action')->orderBy('action')->pluck('total', 'action');
        $subjects = (clone $query)->selectRaw('subject_type, COUNT(*) AS total')->groupBy('subject_type')->orderByDesc('total')->orderBy('subject_type')->pluck('total', 'subject_type');
        $users = (clone $query)->whereNotNull('actor_id')->selectRaw('actor_id, COUNT(*) AS total')
            ->groupBy('actor_id')->orderByDesc('total')->orderBy('actor_id')->limit(50)->get();
        $recent = (clone $query)->orderByDesc('created_at')->orderByDesc('id')->limit(100)->get();

        return response()->view('entries.activity-stats', compact('total','uniqueActors','actions','subjects','users','recent','from','actorId'),200,[
            'Cache-Control' => 'private, no-store, max-age=0',
            'Pragma' => 'no-cache', 'X-Robots-Tag' => 'noindex, nofollow, noarchive',
            'X-Content-Type-Options' => 'nosniff', 'X-Frame-Options' => 'DENY',
            'Referrer-Policy' => 'no-referrer',
            'Content-Security-Policy' => "default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'",
        ]);
    }
}
