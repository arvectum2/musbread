<?php

declare(strict_types=1);

namespace App\Support;

use App\Models\MuseumEntry;
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
        $publishedEventIds = \App\Models\MuseumEvent::query()->public()->pluck('id')->flip();

        $records = [];
        $errors = 0;
        $warnings = 0;
        $ready = 0;
        foreach ($query->get() as $entry) {
            $state = $this->state($entry, $approvedIds);
            if ($state === 'ready') $ready++;
            $issues = $this->issues($entry, $publicIds, $publishedEventIds);
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

        return [
            'total' => count($records), 'ready' => $ready,
            'errors' => $errors, 'warnings' => $warnings, 'records' => $records,
        ];
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
        $plainBody = html_entity_decode(strip_tags((string) $entry->body), ENT_QUOTES | ENT_HTML5, 'UTF-8');
        // Unicode NBSP, narrow NBSP and ideographic whitespace are also blank.
        if (preg_match('/[^\s\p{Z}]/u', $plainBody) !== 1) {
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
