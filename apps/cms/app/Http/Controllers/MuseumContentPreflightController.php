<?php

declare(strict_types=1);

namespace App\Http\Controllers;

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

        return response()->view('entries.preflight', [
            'report' => $service->report($actor),
            'mayRequestExport' => $actor->isSuperUser(),
            'exportQueueConfigured' => (bool) config('museum.queue_publication', false)
                && in_array(config('queue.default'), ['database', 'redis'], true)
                && in_array(config('cache.default'), ['database', 'redis'], true),
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
