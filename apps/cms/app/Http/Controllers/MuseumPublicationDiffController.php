<?php

declare(strict_types=1);

namespace App\Http\Controllers;

use App\Support\MuseumPublicationDiff;
use App\Support\MuseumSectionAccess;
use Illuminate\Http\Response;

/** Local pre-release comparison, never a release or approval endpoint. */
final class MuseumPublicationDiffController extends Controller
{
    public function index(MuseumPublicationDiff $service): Response
    {
        $user = MuseumSectionAccess::user();
        if ($user === null) abort(403);
        try {
            $comparison = $service->report($user);
            $error = null;
        } catch (\Throwable $exception) {
            // Do not show raw exception text or local paths to editors.
            report($exception);
            $comparison = null;
            $error = 'Не удалось собрать временную подготовленную версию. Проверьте материалы и файлы в предпубликационном отчёте.';
        }
        return response()->view('entries.publication-diff', [
            'comparison' => $comparison, 'error' => $error,
        ], 200, [
            'Cache-Control' => 'private, no-store, max-age=0',
            'Pragma' => 'no-cache',
            'X-Robots-Tag' => 'noindex, nofollow, noarchive',
            'X-Content-Type-Options' => 'nosniff',
            'X-Frame-Options' => 'DENY',
            'Referrer-Policy' => 'no-referrer',
            'Content-Security-Policy' => "default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'",
        ]);
    }
}
