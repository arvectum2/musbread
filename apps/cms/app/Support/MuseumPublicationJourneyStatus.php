<?php

declare(strict_types=1);

namespace App\Support;

use App\Models\MuseumContentApproval;
use App\Models\MuseumExportContentProof;
use App\Models\MuseumEntry;
use App\Models\MuseumEvent;
use App\Models\MuseumPublicationRun;
use App\Models\MuseumSection;
use Illuminate\Database\Eloquent\Collection;

/**
 * Read-only evidence for the private editorial approval / export workflow.
 *
 * A completed *private snapshot* is never presented as a public deployment,
 * nor as proof that a coalesced approval was included in a specific snapshot.
 * No user-submitted markup or unpublished media is rendered here.
 */
final class MuseumPublicationJourneyStatus
{
    public const RUN_LABELS = [
        'queued' => 'Ожидает фонового обработчика',
        'running' => 'Подготовка приватного пакета выполняется',
        'succeeded' => 'Приватный пакет подготовлен',
        'failed' => 'Ошибка подготовки приватного пакета',
        'abandoned' => 'Попытки прекращены, требуется проверка',
    ];

    public const DISPATCH_LABELS = [
        'pending' => 'Одобрено; запрос выгрузки ещё не подтверждён',
        'failed' => 'Одобрено; постановка в очередь завершилась ошибкой',
        'queued' => 'Запрос на закрытую выгрузку зарегистрирован',
    ];

    /**
     * @param Collection<int,MuseumContentApproval> $approvals
     * @return array<int,array{approval:MuseumContentApproval,subject_label:string,revision_status:string,dispatch_label:string,run:MuseumPublicationRun|null,run_label:string}>
     */
    public function describe(Collection $approvals): array
    {
        $ids = ['entry' => [], 'event' => [], 'section' => [], 'run' => []];
        foreach ($approvals as $approval) {
            if ($approval->museum_entry_id !== null) $ids['entry'][] = $approval->museum_entry_id;
            if ($approval->museum_event_id !== null) $ids['event'][] = $approval->museum_event_id;
            if ($approval->museum_section_id !== null) $ids['section'][] = $approval->museum_section_id;
            if ($approval->publication_run_id !== null) $ids['run'][] = $approval->publication_run_id;
        }

        $entries = MuseumEntry::query()->whereIn('id', $ids['entry'])->get()->keyBy('id');
        $events = MuseumEvent::query()->whereIn('id', $ids['event'])->get()->keyBy('id');
        $sections = MuseumSection::query()->whereIn('id', $ids['section'])->get()->keyBy('id');
        $runs = MuseumPublicationRun::query()->whereIn('id', $ids['run'])->get()->keyBy('id');
        // Coalesced approvals can appear in a later run unrelated to their
        // initial dispatch. Only completed, hash-matching proof runs count.
        $proofs = MuseumExportContentProof::query()
            ->whereIn('approval_id', $approvals->modelKeys())
            ->orderByDesc('publication_run_id')->get()->groupBy('approval_id');
        $proofRuns = MuseumPublicationRun::query()->whereIn(
            'id', $proofs->flatten(1)->pluck('publication_run_id')->unique()->all()
        )->get()->keyBy('id');

        $out = [];
        foreach ($approvals as $approval) {
            [$subject, $subjectLabel] = match (true) {
                $approval->museum_entry_id !== null => [
                    $entries->get($approval->museum_entry_id), 'Материал #'.$approval->museum_entry_id,
                ],
                $approval->museum_event_id !== null => [
                    $events->get($approval->museum_event_id), 'Событие #'.$approval->museum_event_id,
                ],
                default => [
                    $sections->get($approval->museum_section_id), 'Раздел #'.$approval->museum_section_id,
                ],
            };
            $revisionStatus = $subject === null
                ? 'Объект отсутствует в текущей CMS; старое одобрение сохранено в истории'
                : (hash_equals(
                    (string) $approval->revision_sha256,
                    MuseumApprovalRevision::forSubject($subject)
                )
                    ? 'SHA-256 совпадает с текущей редакцией'
                    : 'Редакция изменилась после одобрения; требуется новое решение');

            $run = $approval->publication_run_id !== null
                ? $runs->get($approval->publication_run_id) : null;
            $runLabel = $run !== null
                ? (self::RUN_LABELS[$run->status] ?? 'Неизвестное состояние запуска')
                : ($approval->publication_run_id === null
                    ? 'Запуск ещё не привязан'
                    : 'Связанный запуск отсутствует в базе');

            $includedProof = null;
            foreach ($proofs->get($approval->id, collect()) as $proof) {
                $evidenceRun = $proofRuns->get($proof->publication_run_id);
                if ($evidenceRun !== null && $evidenceRun->status === 'succeeded'
                    && $evidenceRun->content_verified_at !== null
                    && $evidenceRun->snapshot_sha256 === $proof->snapshot_sha256) {
                    $includedProof = $proof;
                    break;
                }
            }

            $out[] = [
                'approval' => $approval,
                'subject_label' => $subjectLabel,
                'revision_status' => $revisionStatus,
                'dispatch_label' => self::DISPATCH_LABELS[$approval->dispatch_status]
                    ?? 'Неизвестный статус постановки в очередь',
                'run' => $run,
                'run_label' => $runLabel,
                'included_proof' => $includedProof,
            ];
        }
        return $out;
    }
}
