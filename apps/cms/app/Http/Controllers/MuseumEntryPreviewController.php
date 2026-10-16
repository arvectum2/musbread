<?php

declare(strict_types=1);

namespace App\Http\Controllers;

use App\Models\MuseumEntry;
use App\Support\MuseumHtmlSanitizer;
use App\Support\MuseumSectionAccess;
use Illuminate\Http\Response;

/** A saved-record preview: never a publishing endpoint or a public route. */
final class MuseumEntryPreviewController extends Controller
{
    public function show(string $entry, MuseumHtmlSanitizer $sanitizer): Response
    {
        $user = MuseumSectionAccess::user();
        if ($user === null || ! ctype_digit($entry)) abort(404);

        // Query-scoped access control prevents guessing other sections' draft IDs.
        $record = MuseumEntry::query()->editableBy($user)->findOrFail($entry);

        return response()->view('entries.preview', [
            'entry' => $record,
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
