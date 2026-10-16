<?php

declare(strict_types=1);

namespace App\Support;

use App\Models\MuseumEntry;
use App\Models\MuseumEvent;
use Illuminate\Support\Collection;
use Illuminate\Support\Facades\Storage;
use MoonShine\Laravel\Models\MoonshineUser;

/** Read-only editorial review. Hard export eligibility still belongs to museum:export. */
final class MuseumContentPreflight
{
    /** @return array{total:int, ready:int, errors:int, warnings:int, records:array<int,array<string,mixed>>} */
    public function report(?MoonshineUser $actor = null): array
    {
        $query = MuseumEntry::query()
            ->with(['section:id,title', 'media', 'documents', 'relatedEntries:id', 'linkedEvents:id'])
            ->orderBy('type')->orderBy('slug');
        if ($actor !== null) $query->editableBy($actor);

        $approvedIds = MuseumEntryPublicationState::publishedSectionIds();
        $publicIds = MuseumEntry::query()->public()
            ->where(static fn ($q) => $q->whereNull('museum_section_id')
                ->when($approvedIds !== [], static fn ($q) => $q->orWhereIn('museum_section_id', $approvedIds)))
            ->pluck('id')->flip();
        $publishedEventIds = MuseumEvent::query()->public()->pluck('id')->flip();
        $availablePaths = collect();
        $prefixes = array_flip(MuseumInternalLinkInspector::entryPrefixes());
        foreach (MuseumEntry::query()->public()->where(static fn ($q) =>
            $q->whereNull('museum_section_id')->when($approvedIds !== [],
                static fn ($q) => $q->orWhereIn('museum_section_id', $approvedIds)))
            ->with(['documents:id,museum_entry_id,sha256,file_type', 'media:id,museum_entry_id,sha256'])
            ->get(['id', 'type', 'slug', 'title_en', 'body_en']) as $published) {
            $prefix = $prefixes[$published->type] ?? null;
            if ($prefix === null || ! $this->validSlug($published->slug)) continue;
            $availablePaths->put('/'.$prefix.'/'.$published->slug.'/', true);
            if (trim((string) $published->title_en) !== '' && trim((string) $published->body_en) !== '') {
                $availablePaths->put('/en/'.$prefix.'/'.$published->slug.'/', true);
            }
            foreach ($published->documents as $document) {
                if (preg_match('/^[a-f0-9]{64}$/D', (string) $document->sha256)
                    && in_array($document->file_type, ['pdf', 'docx', 'xlsx'], true)) {
                    $availablePaths->put('/documents/'.$document->sha256.'.'.$document->file_type.'/', true);
                }
            }
            foreach ($published->media as $image) {
                if (preg_match('/^[a-f0-9]{64}$/D', (string) $image->sha256)) {
                    $availablePaths->put('/media/'.$image->sha256.'.webp/', true);
                }
            }
        }
        foreach (MuseumEvent::query()->public()->get(['slug']) as $published) {
            if ($this->validSlug($published->slug)) {
                $availablePaths->put('/events/'.$published->slug.'/', true);
            }
        }
        $linkInspector = new MuseumInternalLinkInspector($availablePaths);

        $records = [];
        $errors = 0;
        $warnings = 0;
        $ready = 0;
        foreach ($query->get() as $entry) {
            $state = $this->state($entry, $approvedIds);
            if ($state === 'ready') $ready++;
            $issues = $this->issues($entry, $publicIds, $publishedEventIds);
            $prefix = $prefixes[$entry->type] ?? 'museum';
            // A partial English draft is not exported. It must not block a
            // valid Russian publication (translation_incomplete is a warning).
            $englishLinks = trim((string) $entry->title_en) !== ''
                && trim((string) $entry->body_en) !== ''
                    ? $linkInspector->check((string) $entry->body_en, '/en/'.$prefix.'/'.$entry->slug.'/')
                    : [];
            $issues = array_merge($issues,
                $linkInspector->check((string) $entry->body, '/'.$prefix.'/'.$entry->slug.'/'),
                $englishLinks);
            $counts = [
                'error' => count(array_filter($issues, static fn ($issue) => $issue['level'] === 'error')),
                'warning' => count(array_filter($issues, static fn ($issue) => $issue['level'] === 'warning')),
            ];
            if ($state === 'ready') $errors += $counts['error'];
            $warnings += $counts['warning'];
            $records[] = [
                'id' => $entry->id, 'title' => $entry->title, 'type' => $entry->type,
                'slug' => $entry->slug, 'section' => $entry->section?->title,
                'state' => $state, 'issues' => $issues, 'error_count' => $counts['error'],
                'warning_count' => $counts['warning'],
            ];
        }

        $events = [];
        $eventsReady = 0;
        $eventErrors = 0;
        foreach (MuseumEvent::query()->with('relatedEntries:id')->orderBy('starts_at')->orderBy('slug')->get() as $event) {
            $state = $this->eventState($event);
            if ($state === 'ready') $eventsReady++;
            $issues = $this->eventIssues($event, $publicIds);
            $issues = array_merge($issues,
                $linkInspector->check((string) $event->body, '/events/'.$event->slug.'/'));
            $errorCount = count(array_filter($issues, static fn ($issue) => $issue['level'] === 'error'));
            $warningCount = count(array_filter($issues, static fn ($issue) => $issue['level'] === 'warning'));
            if ($state === 'ready') {
                $errors += $errorCount;
                $eventErrors += $errorCount;
            }
            $warnings += $warningCount;
            $events[] = [
                'id' => $event->id, 'title' => $event->title, 'slug' => $event->slug,
                'category' => $event->category, 'starts_at' => $event->starts_at?->format('Y-m-d'),
                'ends_at' => $event->ends_at?->format('Y-m-d'),
                'state' => $state, 'issues' => $issues,
                'error_count' => $errorCount, 'warning_count' => $warningCount,
            ];
        }

        return [
            'total' => count($records), 'ready' => $ready,
            'events_total' => count($events), 'events_ready' => $eventsReady,
            'event_errors' => $eventErrors, 'events' => $events,
            'errors' => $errors, 'warnings' => $warnings, 'records' => $records,
        ];
    }

    private function validSlug(?string $slug): bool
    {
        return preg_match('/^[a-z0-9]+(?:-[a-z0-9]+)*$/D', (string) $slug) === 1;
    }

    private function eventState(MuseumEvent $event): string
    {
        if ($event->status !== 'published') return 'draft';
        if ($event->published_at === null || $event->published_at->isFuture()) return 'scheduled';
        return 'ready';
    }

    /** @return list<array{level:string,code:string,message:string}> */
    private function eventIssues(MuseumEvent $event, Collection $publicIds): array
    {
        $issues = [];
        $add = static function (string $level, string $code, string $message) use (&$issues): void {
            $issues[] = compact('level', 'code', 'message');
        };
        if (trim((string) $event->title) === '') $add('error', 'event_title_missing', 'У события нет названия.');
        if (! $this->validSlug($event->slug)) $add('error', 'event_slug_invalid', 'Неверный URL события.');
        if (trim((string) $event->category) === '') $add('error', 'event_category_missing', 'Не задана категория события.');
        if ($event->starts_at === null) $add('error', 'event_date_missing', 'Не задана дата события.');
        if ($event->ends_at !== null && $event->starts_at !== null && $event->ends_at->isBefore($event->starts_at)) {
            $add('error', 'event_date_range_invalid', 'Дата окончания раньше даты начала.');
        }
        if (! $this->hasText($event->excerpt)) $add('error', 'event_excerpt_missing', 'Не заполнен анонс события.');
        if (! $this->hasText($event->body)) $add('error', 'event_body_missing', 'Не заполнено описание события.');
        if (($event->ends_at ?? $event->starts_at)?->isBefore(today())) {
            $add('warning', 'event_past', 'Событие завершилось: сохраните в публичном архиве, если публикация одобрена.');
        }
        if (trim((string) $event->seo_title) === '') {
            $add('warning', 'event_seo_title_missing', 'Нет SEO-заголовка события: будет применён шаблон сайта.');
        }
        if (trim((string) $event->seo_description) === '') {
            $add('warning', 'event_seo_description_missing', 'Нет SEO-описания события.');
        }
        if ($event->relatedEntries->contains(static fn ($entry) => ! $publicIds->has($entry->id))) {
            $add('warning', 'event_relation_unpublished', 'Некоторые связанные с событием страницы не попадут в выгрузку.');
        }
        return $issues;
    }

    private function hasText(?string $html): bool
    {
        $text = html_entity_decode(strip_tags((string) $html), ENT_QUOTES | ENT_HTML5, 'UTF-8');
        return preg_match('/[^\s\p{Z}]/u', $text) === 1;
    }

    /** @param list<int> $approvedIds */
    private function state(MuseumEntry $entry, array $approvedIds): string
    {
        if ($entry->status !== 'published') return 'draft';
        if ($entry->published_at === null || $entry->published_at->isFuture()) return 'scheduled';
        if ($entry->museum_section_id !== null
            && ! in_array($entry->museum_section_id, $approvedIds, true)) return 'blocked';
        return 'ready';
    }

    /**
     * @return array<int,array{level:string,code:string,message:string}>
     */
    private function issues(MuseumEntry $entry, $publicIds, $publishedEventIds): array
    {
        $issues = [];
        $add = static function (string $level, string $code, string $message) use (&$issues): void {
            $issues[] = compact('level', 'code', 'message');
        };
        if (trim((string) $entry->title) === '') {
            $add('error', 'title_missing', 'Не заполнено название.');
        }
        if (! preg_match('/^[a-z0-9]+(?:-[a-z0-9]+)*$/D', (string) $entry->slug)) {
            $add('error', 'slug_invalid', 'Неверный URL: допустимы латинские буквы, цифры и дефисы.');
        }
        if (! array_key_exists($entry->type, MuseumEntry::TYPES)) {
            $add('error', 'type_invalid', 'Неизвестный тип материала.');
        }
        // An HTML fragment with only tags/whitespace is not meaningful content.
        if (! $this->hasText($entry->body)) {
            $add('error', 'body_missing', 'Основной текст пуст или состоит только из HTML-тегов.');
        }
        if (trim((string) $entry->h1) === '') {
            $add('warning', 'h1_missing', 'H1 не заполнен: проверьте заголовок страницы.');
        }
        if (in_array($entry->type, ['news', 'excursion', 'exhibition'], true)
            && trim((string) $entry->excerpt) === '') {
            $add('warning', 'excerpt_missing', 'Нет краткого анонса для карточек и списков.');
        }
        if (trim((string) $entry->seo_title) === '') {
            $add('warning', 'seo_title_missing', 'SEO-заголовок не заполнен: будет применён шаблон сайта.');
        }
        if (trim((string) $entry->seo_description) === '') {
            $add('warning', 'seo_description_missing', 'SEO-описание не заполнено: проверьте сниппет.');
        }
        if ((trim((string) $entry->title_en) === '') !== (trim((string) $entry->body_en) === '')) {
            $add('warning', 'translation_incomplete', 'Английская версия неполная и не появится в публикации.');
        }
        if ($entry->type === 'document' && $entry->documents->isEmpty()) {
            $add('warning', 'document_missing', 'У страницы документа нет прикреплённого файла.');
        }

        foreach ($entry->documents as $document) {
            if (! $document->accessibility_reviewed) {
                $add('warning', 'document_accessibility', 'У одного из документов не подтверждена доступность.');
                break;
            }
        }
        foreach ($entry->media as $media) {
            if (trim((string) $media->alt) === '') {
                $add('warning', 'media_alt_missing', 'У изображения отсутствует alt-описание.');
                break;
            }
        }
        foreach (['media' => $entry->media, 'documents' => $entry->documents] as $type => $files) {
            foreach ($files as $file) {
                // The exporter already validates file type, format and checksum;
                // this quick preflight catches missing assets without mutating storage.
                if (! Storage::disk('local')->exists($file->storage_path)) {
                    $add('error', $type.'_file_missing', 'Прикреплённый файл отсутствует в закрытом хранилище.');
                    break;
                }
            }
        }
        if ($entry->relatedEntries->contains(static fn ($target) => ! $publicIds->has($target->id))
            || $entry->linkedEvents->contains(static fn ($target) => ! $publishedEventIds->has($target->id))) {
            // No target title, ID or section is revealed to a restricted editor.
            $add('warning', 'related_unpublished', 'Часть связанных материалов или событий не попадёт в ближайшую выгрузку.');
        }

        return $issues;
    }
}
