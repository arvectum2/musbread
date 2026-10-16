<?php

declare(strict_types=1);

namespace App\Http\Controllers;

use App\Support\MuseumPublicationDiff;
use App\Support\MuseumSectionAccess;
use Illuminate\Http\Response;

/** Private read-only review worksheet. No redirects are installed automatically. */
final class MuseumRemovedUrlsController extends Controller
{
    public function download(MuseumPublicationDiff $service): Response
    {
        $user = MuseumSectionAccess::user();
        if ($user === null) abort(403);
        try {
            $comparison = $service->report($user);
        } catch (\Throwable $e) {
            report($e);
            abort(503, 'Не удалось сформировать предварительный снимок.');
        }
        if (! $comparison['baseline_available']) {
            abort(409, 'Подтверждённый локальный базовый снимок недоступен.');
        }
        $buffer = fopen('php://temp', 'w+');
        if ($buffer === false) abort(500);
        try {
            fwrite($buffer, "\xEF\xBB\xBF");
            fputcsv($buffer, ['Старый URL', 'Язык', 'Сущность', 'Материал', 'Новый URL (согласовать)', 'Решение редактора'], ';', '"', '');
            foreach ($comparison['removed_urls'] as $item) {
                $title = (string) $item['title'];
                // Prevent CSV formula injection from old CMS titles in Excel.
                if (preg_match('/^[\s\x00-\x1F]*[=+@-]/u', $title) === 1) $title = "'".$title;
                fputcsv($buffer, [$item['path'], $item['locale'], $item['kind'],
                    $title, '', 'Проверить необходимость перенаправления'], ';', '"', '');
            }
            rewind($buffer);
            $csv = stream_get_contents($buffer);
        } finally {
            fclose($buffer);
        }
        return response($csv, 200, [
            'Content-Type' => 'text/csv; charset=UTF-8',
            'Content-Disposition' => 'attachment; filename="musbread-removed-urls.csv"',
            'Cache-Control' => 'private, no-store, max-age=0',
            'X-Robots-Tag' => 'noindex, nofollow, noarchive',
            'X-Content-Type-Options' => 'nosniff',
            'Referrer-Policy' => 'no-referrer',
        ]);
    }
}
