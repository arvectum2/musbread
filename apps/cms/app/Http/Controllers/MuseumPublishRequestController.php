<?php

declare(strict_types=1);

namespace App\Http\Controllers;

use App\Support\MuseumContentPreflight;
use App\Support\MuseumSectionAccess;
use Illuminate\Http\RedirectResponse;
use Illuminate\Support\Facades\Artisan;

/**
 * Admin-only, CSRF-protected manual export queue request.
 * IMPORTANT: "queued" means a PRIVATE CMS export, NOT public deployment.
 */
final class MuseumPublishRequestController extends Controller
{
    public function store(MuseumContentPreflight $preflight): RedirectResponse
    {
        $actor = MuseumSectionAccess::user();
        if ($actor === null || ! $actor->isSuperUser()) abort(403);
        if (! config('museum.queue_publication', false)
            || ! in_array(config('queue.default'), ['database', 'redis'], true)
            || ! in_array(config('cache.default'), ['database', 'redis'], true)) {
            abort(409, 'Недоступна проверенная постоянная очередь выгрузки.');
        }
        // Same strict contract as the scheduled queue job. Fail BEFORE
        // dispatching even though the worker also performs strict preflight.
        if (($preflight->report()['errors'] ?? 1) > 0) {
            abort(422, 'Есть критические ошибки, пакет выгрузки не поставлен в очередь.');
        }
        if (Artisan::call('museum:queue-export') !== 0) {
            abort(503, 'Не удалось поставить пакет на подготовку.');
        }

        return redirect()->route('museum.content.preflight')
            ->with('museum_export_queue_result',
                'Запрос выгрузки обработан. Проверьте закрытый журнал запусков. '
                .'Это не подтверждение обновления публичного сайта.');
    }
}
