<?php

declare(strict_types=1);

namespace App\Http\Controllers;

use App\Models\MuseumEvent;
use App\Support\MuseumHtmlSanitizer;
use App\Support\MuseumSectionAccess;
use Illuminate\Http\Response;

/** Closed, read-only preview of a saved event; does not publish it. */
final class MuseumEventPreviewController extends Controller
{
    public function show(string $event, MuseumHtmlSanitizer $sanitizer): Response
    {
        // Event CRUD is available to authenticated MoonShine editors; its
        // current model has no per-section access grants, unlike MuseumEntry.
        if (MuseumSectionAccess::user() === null || ! ctype_digit($event)) abort(404);
        $record = MuseumEvent::query()->findOrFail($event);

        return response()->view('events.preview', [
            'event' => $record,
            'cleanBody' => $sanitizer->clean((string) $record->body),
        ], 200, [
            'Cache-Control' => 'private, no-store, max-age=0',
            'Pragma' => 'no-cache',
            'X-Robots-Tag' => 'noindex, nofollow, noarchive',
            'X-Content-Type-Options' => 'nosniff',
            'X-Frame-Options' => 'DENY',
            'Referrer-Policy' => 'no-referrer',
            'Content-Security-Policy' => "default-src 'none'; style-src 'unsafe-inline'; "
                ."base-uri 'none'; object-src 'none'; form-action 'none'; frame-ancestors 'none'",
        ]);
    }
}
