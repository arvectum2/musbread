<?php

declare(strict_types=1);

namespace App\Http\Controllers;

use App\Support\MuseumReleaseReviewPack;
use App\Support\MuseumSectionAccess;
use Illuminate\Http\Response;

/** Authenticated read-only JSON report, never a sign-off or publishing action. */
final class MuseumReleaseReviewPackController extends Controller
{
    public function download(MuseumReleaseReviewPack $service): Response
    {
        $user = MuseumSectionAccess::user();
        if ($user === null) abort(403);
        try {
            $pack = $service->prepare($user);
        } catch (\Throwable $exception) {
            report($exception);
            abort(503, 'Не удалось собрать приватный предпубликационный отчёт.');
        }
        if ($pack === null) abort(409, 'Нет подтверждённого локального базового снимка.');

        return response(json_encode($pack, MuseumReleaseReviewPack::JSON_FLAGS)."\n", 200, [
            'Content-Type' => 'application/json; charset=UTF-8',
            'Content-Disposition' => 'attachment; filename="musbread-release-review.json"',
            'Cache-Control' => 'private, no-store, max-age=0',
            'Pragma' => 'no-cache',
            'X-Robots-Tag' => 'noindex, nofollow, noarchive',
            'X-Content-Type-Options' => 'nosniff',
            'X-Frame-Options' => 'DENY',
            'Referrer-Policy' => 'no-referrer',
            'Content-Security-Policy' => "default-src 'none'; base-uri 'none'; frame-ancestors 'none'",
        ]);
    }
}
