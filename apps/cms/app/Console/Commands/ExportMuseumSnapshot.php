<?php

namespace App\Console\Commands;

use App\Models\MuseumEvent;
use App\Models\MuseumEntry;
use App\Models\MuseumSection;
use App\Support\MuseumDocumentInspector;
use Illuminate\Support\Facades\Storage;
use Illuminate\Console\Command;

class ExportMuseumSnapshot extends Command
{
    protected $signature = 'museum:export {--output= : Path to generated JSON} {--manifest= : Path to integrity manifest} {--media-output-dir= : Destination for static WebP assets} {--document-output-dir= : Destination for downloadable approved documents} {--preflight-strict : Abort before writing when public-ready entries or events have critical editorial issues}';
    protected $description = 'Publish approved CMS content into an offline static-site snapshot';

    public function handle(): int
    {
        if ($this->option('preflight-strict')
            && app(\App\Support\MuseumContentPreflight::class)->report()['errors'] > 0) {
            $this->error('Предпубликационная проверка выявила критические ошибки. Экспорт не выполнялся. См. museum:preflight.');
            return self::FAILURE;
        }
        $output = $this->option('output') ?: base_path('../web/src/data/published.json');
        $manifest = $this->option('manifest') ?: base_path('../web/public/snapshot-manifest.json');
        $mediaDir = $this->option('media-output-dir') ?: base_path('../web/public/media');
        $mediaFiles = [];
        $documentDir = $this->option('document-output-dir') ?: base_path('../web/public/documents');
        $documentFiles = [];
        $inspector = app(MuseumDocumentInspector::class);

        $publicEvents = MuseumEvent::query()
            ->public()->with('relatedEntries')
            ->orderBy('starts_at')->orderBy('slug')->get();

        // A section is public only when all its ancestors are approved as well.
        // No editing rights, user emails or permission mappings leave the CMS.
        $allSections = MuseumSection::query()->orderByRaw('CASE WHEN parent_id IS NULL THEN 0 ELSE 1 END')->orderBy('sort_order')->orderBy('slug')->get();
        $byId = $allSections->keyBy('id');
        $publishedSections = $allSections->filter(static function (MuseumSection $section) use ($byId): bool {
            $seen = [];
            $node = $section;
            while ($node !== null) {
                if ($node->status !== 'published' || isset($seen[$node->id])) return false;
                $seen[$node->id] = true;
                if ($node->parent_id !== null && ! $byId->has($node->parent_id)) return false;
                $node = $node->parent_id === null ? null : $byId->get($node->parent_id);
            }
            return true;
        });
        $approvedIds = $publishedSections->modelKeys();
        $sections = $publishedSections->map(static fn (MuseumSection $section) => [
            'slug' => $section->slug,
            'title' => $section->title,
            'parent_slug' => $section->parent_id === null ? null : $byId->get($section->parent_id)?->slug,
            'sort_order' => $section->sort_order,
            'legacy_path' => $section->legacy_path,
        ])->values()->all();

        $publicEntries = MuseumEntry::query()
            ->public()
            ->orderBy('type')
            ->orderBy('sort_order')
            ->orderBy('slug')
            ->with(['media', 'documents', 'section', 'relatedEntries', 'linkedEvents'])
            ->get()
            ->filter(static fn (MuseumEntry $entry) =>
                $entry->museum_section_id === null || in_array($entry->museum_section_id, $approvedIds, true));

        // Resolve relation links ONLY among approved public records (including
        // the section ancestor check). IDs and CMS pivot rows stay private.
        $entryById = $publicEntries->keyBy('id');
        $eventById = $publicEvents->keyBy('id');
        $typePaths = [
            'page' => 'museum', 'news' => 'news', 'excursion' => 'excursions',
            'exhibition' => 'exhibitions', 'document' => 'documents',
        ];
        $entryLink = static function (MuseumEntry $candidate) use ($typePaths): ?array {
            if (! isset($typePaths[$candidate->type])
                || ! preg_match('/^[a-z0-9]+(?:-[a-z0-9]+)*$/D', $candidate->slug)) return null;
            return [
                'type' => $candidate->type, 'title' => $candidate->title,
                'href' => '/'.$typePaths[$candidate->type].'/'.$candidate->slug.'/',
            ];
        };
        $publicLinks = static function ($related, $byId, $link): array {
            return $related->filter(static fn ($candidate) => $byId->has($candidate->id))
                ->sortBy(static fn ($candidate) => $candidate->title.'|'.$candidate->id)
                ->map($link)->filter()->values()->all();
        };
        $eventLink = static function (MuseumEvent $event): ?array {
            if (! preg_match('/^[a-z0-9]+(?:-[a-z0-9]+)*$/D', $event->slug)) return null;
            return ['title' => $event->title, 'href' => '/events/'.$event->slug.'/'];
        };

        $events = $publicEvents->map(static function (MuseumEvent $event) use ($entryById, $entryLink, $publicLinks): array {
            $out = [
                'slug' => $event->slug, 'title' => $event->title,
                'category' => $event->category,
                'date' => $event->starts_at->format('Y-m-d'),
                'excerpt' => $event->excerpt, 'body' => $event->body,
            ];
            $related = $publicLinks($event->relatedEntries, $entryById, $entryLink);
            if ($related !== []) $out['related_entries'] = $related;
            return $out;
        })->all();

        $entries = $publicEntries
            ->map(function (MuseumEntry $entry) use (&$mediaFiles, &$documentFiles, $mediaDir, $documentDir, $inspector,
                $entryById, $eventById, $entryLink, $eventLink, $publicLinks): array {
                $images = [];
                foreach ($entry->media as $image) {
                    $raw = Storage::disk('local')->get($image->storage_path);
                    if (! is_string($raw) || hash('sha256', $raw) !== $image->sha256
                        || strlen($raw) !== $image->size_bytes
                        || (@getimagesizefromstring($raw)[2] ?? null) !== IMAGETYPE_WEBP) {
                        throw new \RuntimeException('Uploaded image checksum or format invalid: '.$image->id);
                    }
                    if (! is_dir($mediaDir) && ! mkdir($mediaDir, 0755, true) && ! is_dir($mediaDir)) {
                        throw new \RuntimeException('Cannot create public media directory');
                    }
                    if (! preg_match('/^[a-f0-9]{64}$/D', $image->sha256)) {
                        throw new \RuntimeException('Invalid image digest');
                    }
                    $target = rtrim($mediaDir, '/').'/'.$image->sha256.'.webp';
                    if (! is_file($target) || hash_file('sha256', $target) !== $image->sha256) {
                        $tmp = $target.'.tmp.'.getmypid();
                        if (file_put_contents($tmp, $raw, LOCK_EX) === false || ! rename($tmp, $target)) {
                            throw new \RuntimeException('Cannot publish media file');
                        }
                    }
                    $mediaFiles['media/'.$image->sha256.'.webp'] = [
                        'sha256' => $image->sha256, 'bytes' => $image->size_bytes,
                    ];
                    $images[] = [
                        'src' => '/media/'.$image->sha256.'.webp',
                        'alt' => $image->alt, 'caption' => $image->caption,
                        'width' => $image->width, 'height' => $image->height,
                    ];
                }
                $documents = [];
                foreach ($entry->documents as $document) {
                    $path = Storage::disk('local')->path($document->storage_path);
                    if (! is_file($path) || hash_file('sha256', $path) !== $document->sha256
                        || filesize($path) !== $document->size_bytes
                        || ! in_array($document->file_type, ['pdf', 'docx', 'xlsx'], true)) {
                        throw new \RuntimeException('Document checksum or format invalid: '.$document->id);
                    }
                    $inspector->verify($path, $document->file_type);
                    if (! preg_match('/^[a-f0-9]{64}$/D', $document->sha256)) {
                        throw new \RuntimeException('Invalid document digest');
                    }
                    if (! is_dir($documentDir) && ! mkdir($documentDir, 0755, true) && ! is_dir($documentDir)) {
                        throw new \RuntimeException('Cannot create static document directory');
                    }
                    $name = $document->sha256.'.'.$document->file_type;
                    $target = rtrim($documentDir, '/').'/'.$name;
                    if (! is_file($target) || hash_file('sha256', $target) !== $document->sha256) {
                        $temp = $target.'.tmp.'.getmypid();
                        if (! copy($path, $temp) || ! rename($temp, $target)) {
                            throw new \RuntimeException('Cannot publish document');
                        }
                    }
                    $documentFiles['documents/'.$name] = [
                        'sha256' => $document->sha256, 'bytes' => $document->size_bytes,
                    ];
                    $documents[] = [
                        'href' => '/documents/'.$name,
                        'label' => $document->label,
                        'format' => $document->file_type,
                        'size_bytes' => $document->size_bytes,
                        'accessibility_reviewed' => $document->accessibility_reviewed,
                        // Unreviewed editorial notes must never leak to the public JSON.
                        'accessibility_note' => $document->accessibility_reviewed
                            ? $document->accessibility_note : null,
                    ];
                }

                return array_filter([
                'type' => $entry->type,
                'slug' => $entry->slug,
                'title' => $entry->title,
                'h1' => $entry->h1,
                'parent_slug' => $entry->parent_slug,
                'section_slug' => $entry->section?->slug,
                'excerpt' => $entry->excerpt,
                'body' => $entry->body,
                'seo_title' => $entry->seo_title,
                'seo_description' => $entry->seo_description,
                'sort_order' => $entry->sort_order,
                'related_entries' => $publicLinks($entry->relatedEntries, $entryById, $entryLink),
                'related_events' => $publicLinks($entry->linkedEvents, $eventById, $eventLink),
                'media' => $images,
                'documents' => $documents,
                'translations' => trim((string) $entry->title_en) !== ''
                    && trim((string) $entry->body_en) !== '' ? [
                        'en' => [
                            'title' => $entry->title_en,
                            'excerpt' => $entry->excerpt_en,
                            'body' => $entry->body_en,
                            'seo_title' => $entry->seo_title_en,
                            'seo_description' => $entry->seo_description_en,
                        ],
                    ] : null,
            ], static function ($value, $key): bool {
                if (in_array($key, ['media', 'documents', 'related_entries', 'related_events'], true)) return count($value) > 0;
                if ($key === 'section_slug' || $key === 'translations') return $value !== null;
                return true;
            }, ARRAY_FILTER_USE_BOTH);
            })->values()->all();

        // Prune assets withdrawn by the editor from this *generated-only* folder.
        // Otherwise a formerly published image would remain publicly accessible.
        if (is_dir($mediaDir)) {
            foreach (glob(rtrim($mediaDir, '/').'/*.webp') ?: [] as $existing) {
                if (! array_key_exists('media/'.basename($existing), $mediaFiles)) {
                    unlink($existing);
                }
            }
        }

        // Withdraw generated documents removed by the editor or hidden by draft status.
        // Never touch arbitrary files beyond the content-addressed export directory.
        if (is_dir($documentDir)) {
            foreach (glob(rtrim($documentDir, '/').'/*') ?: [] as $existing) {
                if (is_file($existing)
                    && preg_match('/^[a-f0-9]{64}\\.(?:pdf|docx|xlsx)$/D', basename($existing))
                    && ! array_key_exists('documents/'.basename($existing), $documentFiles)) {
                    unlink($existing);
                }
            }
        }

        // Public export intentionally excludes draft/private properties, role info and PII.
        $data = [
            'schema_version' => 1,
            'site' => [
                'name' => 'Музей Хлеба',
                'subtitle' => 'Демонстрационная версия · концепция не утверждена',
                'description' => 'Предконтрактный прототип информационного сайта музея.',
            ],
            'events' => $events,
            'entries' => $entries,
        ];
        // Preserve the original schema for fixture parity when the seed is absent.
        // CMS-controlled navigation becomes authoritative once sections are created.
        if ($allSections->isNotEmpty()) {
            $data['sections'] = $sections;
        }
        // Match the Python fixture publisher canonical JSON serializer.
        $normalize = function ($obj) use (&$normalize) {
            if (! is_array($obj)) return $obj;
            if (array_is_list($obj)) return array_map($normalize, $obj);
            ksort($obj);
            return array_map($normalize, $obj);
        };
        $payload = json_encode($normalize($data), JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES | JSON_THROW_ON_ERROR)."\n";
        $audit = [
            'schema_version' => 1,
            'files' => array_merge(['published.json' => ['sha256' => hash('sha256', $payload), 'bytes' => strlen($payload)]], $mediaFiles, $documentFiles),
            'event_count' => count($events),
            'entry_count' => count($entries),
        ];
        if ($allSections->isNotEmpty()) {
            $audit['section_count'] = count($sections);
        }
        $manifestData = json_encode($normalize($audit), JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES | JSON_THROW_ON_ERROR)."\n";

        foreach ([[$output, $payload], [$manifest, $manifestData]] as [$target, $contents]) {
            if (! is_dir(dirname($target))) {
                mkdir(dirname($target), 0755, true);
            }
            $temporary = $target.'.tmp.'.getmypid();
            if (file_put_contents($temporary, $contents, LOCK_EX) === false || ! rename($temporary, $target)) {
                throw new \RuntimeException('Unable to publish snapshot file: '.$target);
            }
        }
        $this->info('Published '.count($events).' events and '.count($entries).' entries; SHA-256='.hash('sha256', $payload));
        return self::SUCCESS;
    }
}
