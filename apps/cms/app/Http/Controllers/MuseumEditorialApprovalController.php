<?php

declare(strict_types=1);

namespace App\Http\Controllers;

use App\Models\MuseumContentApproval;
use App\Models\MuseumEntry;
use App\Models\MuseumEvent;
use App\Models\MuseumSection;
use App\Support\MuseumEntryPublicationState;
use Illuminate\Database\Eloquent\Model;
use App\Models\MuseumPublicationRun;
use App\Support\MuseumApprovalRevision;
use App\Support\MuseumContentPreflight;
use App\Support\MuseumSectionAccess;
use Illuminate\Http\RedirectResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Artisan;
use Illuminate\Support\Facades\Cache;
use Illuminate\Support\Facades\DB;

/**
 * Explicit editorial approval; NEVER interpret saving a published item as approval.
 * Queues a PRIVATE export only. Public deployment requires separate trusted channel.
 */
final class MuseumEditorialApprovalController extends Controller
{
    public function store(Request $request, MuseumEntry $entry, MuseumContentPreflight $preflight): RedirectResponse
    {
        return $this->approve($request, $entry, 'entry', $preflight);
    }

    public function storeEvent(Request $request, MuseumEvent $event, MuseumContentPreflight $preflight): RedirectResponse
    {
        return $this->approve($request, $event, 'event', $preflight);
    }

    public function storeSection(Request $request, MuseumSection $section, MuseumContentPreflight $preflight): RedirectResponse
    {
        return $this->approve($request, $section, 'section', $preflight);
    }

    private function approve(Request $request, Model $subject, string $kind, MuseumContentPreflight $preflight): RedirectResponse
    {
        $actor = MuseumSectionAccess::user();
        if ($actor === null || ! $actor->isSuperUser()) abort(403);

        if (! config('museum.editorial_approval_queue', false)
            || ! config('museum.queue_publication', false)
            || ! in_array(config('queue.default'), ['database', 'redis'], true)
            || ! in_array(config('cache.default'), ['database', 'redis'], true)) {
            abort(409, 'Одобрение с выгрузкой недоступно без постоянных очереди и блокировки.');
        }
        $input = $request->validate(['revision_sha256' => ['required', 'regex:/^[0-9a-f]{64}$/D']]);

        $lock = Cache::lock('museum:editorial-approval:'.$kind.':'.$subject->id, 45);
        if (! $lock->get()) abort(409, 'Другая операция одобрения уже выполняется.');

        try {
            $approval = DB::transaction(function () use ($subject, $kind, $preflight, $input, $actor) {
                $fresh = $subject->newQuery()->lockForUpdate()->findOrFail($subject->id);
                $fingerprint = MuseumApprovalRevision::forSubject($fresh);
                if (! hash_equals($fingerprint, $input['revision_sha256'])) {
                    abort(409, 'Материал изменился после предпросмотра; требуется повторная проверка.');
                }

                // This is an independent explicit action, not a model::saving event.
                $report = $preflight->report();
                $eligible = match ($kind) {
                    'entry', 'event' => collect($report[$kind === 'entry' ? 'records' : 'events'])
                        ->contains(static fn ($row) => $row['id'] === $fresh->id
                            && $row['state'] === 'ready' && $row['error_count'] === 0),
                    'section' => trim((string) $fresh->title) !== ''
                        && in_array($fresh->id, MuseumEntryPublicationState::publishedSectionIds(), true),
                    default => false,
                };
                if (! $eligible || $report['errors'] !== 0) {
                    abort(422, 'Материал, событие или раздел не прошли строгую проверку.');
                }

                $key = match ($kind) {
                    'entry' => 'museum_entry_id',
                    'event' => 'museum_event_id',
                    'section' => 'museum_section_id',
                };
                $existing = MuseumContentApproval::query()
                    ->where($key, $fresh->id)
                    ->where('revision_sha256', $fingerprint)->first();
                if ($existing !== null) {
                    // Original approval timestamp cannot be refreshed by clicking twice.
                    return $existing;
                }
                return MuseumContentApproval::create([
                    $key => $fresh->id,
                    'revision_sha256' => $fingerprint,
                    'actor_id' => $actor->id,
                    'approved_at' => now('UTC'),
                    'dispatch_status' => 'pending',
                ]);
            });

            if ($approval->dispatch_status !== 'queued') {
                // Enqueue only AFTER commit; jobs never read an uncommitted approval.
                try {
                    if (Artisan::call('museum:queue-export') !== 0) {
                        throw new \RuntimeException('Queue export did not succeed');
                    }
                    $run = MuseumPublicationRun::query()
                        ->whereIn('status', ['queued', 'running', 'succeeded'])
                        ->latest('id')->first();
                    if ($run === null) throw new \RuntimeException('No publication run after enqueue');
                    $approval->update([
                        'dispatch_status' => 'queued',
                        'publication_run_id' => $run->id,
                    ]);
                } catch (\Throwable $e) {
                    $approval->update(['dispatch_status' => 'failed']);
                    abort(503, 'Одобрение записано, но очередь недоступна. '
                        .'Повторите запрос после восстановления; время одобрения сохранено.');
                }
            }
            return redirect()->route('museum.content.preflight')
                ->with('museum_export_queue_result',
                    'Редакция одобрена и запрос закрытой выгрузки зарегистрирован. '
                    .'Публичное появление сайта и соблюдение 60 минут ещё не подтверждены.');
        } finally {
            $lock->release();
        }
    }
}
