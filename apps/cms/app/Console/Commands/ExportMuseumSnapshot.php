<?php

namespace App\Console\Commands;

use App\Support\MuseumAltPolicy;
use App\Support\MuseumVideoUrlPolicy;
use App\Models\MuseumEvent;
use App\Models\MuseumEntry;
use App\Models\MuseumSection;
use App\Models\MuseumFixedPageSeo;
use App\Models\MuseumVisitorContacts;
use App\Support\MuseumDocumentInspector;
use Illuminate\Support\Facades\Storage;
use Illuminate\Console\Command;

class ExportMuseumSnapshot extends Command
{
    protected $signature = 'museum:export {--output= : Path to generated JSON} {--manifest= : Path to integrity manifest} {--media-output-dir= : Destination for static WebP assets} {--document-output-dir= : Destination for downloadable approved documents} {--preflight-strict : Abort before writing when public-ready entries or events have critical editorial issues} {--review-pack= : Require an unchanged full admin review JSON before generating output}';
    protected $description = 'Publish approved CMS content into an offline static-site snapshot';

    public function handle(): int
    {
        // The verifier performs a nested ephemeral museum:export. Capture the
        // operator's destinations BEFORE that invocation, otherwise Laravel's
        // shared command instance may replace this call's bound options.
        $reviewPack = $this->option('review-pack');
        $preflightStrict = (bool) $this->option('preflight-strict');
        $output = $this->option('output') ?: base_path('../web/src/data/published.json');
        $manifest = $this->option('manifest') ?: base_path('../web/public/snapshot-manifest.json');
        $mediaDir = $this->option('media-output-dir') ?: base_path('../web/public/media');
        $documentDir = $this->option('document-output-dir') ?: base_path('../web/public/documents');

        if ($reviewPack !== null) {
            $result = app(\App\Support\MuseumReviewPackVerifier::class)
                ->verify((string) $reviewPack);
            if (! $result['ok']) {
                $this->error('Экспорт остановлен до записи файлов: '.$result['message'].' ['.$result['code'].']');
                return self::FAILURE;
            }
        }
        if ($preflightStrict
            && app(\App\Support\MuseumContentPreflight::class)->report()['errors'] > 0) {
            $this->error('Предпубликационная проверка выявила критические ошибки. Экспорт не выполнялся. См. museum:preflight.');
            return self::FAILURE;
        }
        // Fail before ANY generated files are touched, including media/documents.
        // Opt-in only: existing pre-contract fixture export is unchanged.
        try {
            $approvedSet = app(\App\Support\MuseumExplicitApprovalGate::class)->capture();
        } catch (\RuntimeException $exception) {
            $this->error('Approval gate denied export: '.$exception->getMessage());
            return self::FAILURE;
        }
        $mediaFiles = [];
        $documentFiles = [];
        $inspector = app(MuseumDocumentInspector::class);

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
        $publicEvents = MuseumEvent::query()->public()->with(['relatedEntries', 'section', 'coverMedia.entry'])
            ->orderBy('starts_at')->orderBy('slug')->get()
            ->filter(static fn (MuseumEvent $event) =>
                $event->museum_section_id === null || in_array($event->museum_section_id, $approvedIds, true));
        $sections = $publishedSections->map(static fn (MuseumSection $section) => [
            'slug' => $section->slug,
            'title' => $section->title,
            'parent_slug' => $section->parent_id === null ? null : $byId->get($section->parent_id)?->slug,
            'sort_order' => $section->sort_order,
            'legacy_path' => $section->legacy_path,
            // Add only filled optional fields: old seed JSON remains stable
            // and empty placeholders cannot override the page's fallback.
            ...array_filter([
                'h1' => $section->h1,
                'seo_title' => $section->seo_title,
                'seo_description' => $section->seo_description,
            ], static fn ($value): bool => trim((string) $value) !== ''),
        ])->values()->all();

        $publicEntries = MuseumEntry::query()
            ->public()
            ->orderBy('type')
            ->orderBy('sort_order')
            ->orderBy('slug')
            ->with(['media', 'videos', 'documents', 'section', 'relatedEntries', 'linkedEvents'])
            ->get()
            ->filter(static fn (MuseumEntry $entry) =>
                $entry->museum_section_id === null || in_array($entry->museum_section_id, $approvedIds, true));

        // Fail closed BEFORE exporting files if ANY CMS WYSIWYG placeholder
        // points at an unapproved, withdrawn or malformed publisher record.
        // This protects generated document/media directories from partial
        // changes caused by an invalid late-arriving video marker.
        foreach ($publicEntries as $publicEntry) {
            $body = (string) $publicEntry->body;
            preg_match_all('/\\[\\[museum-video:([a-z0-9]+(?:-[a-z0-9]+)*)\\]\\]/',
                $body, $tokens);
            // The public React renderer accepts only isolated TinyMCE
            // paragraphs; reject tokens glued to other text or HTML.
            preg_match_all('~<p(?:\\s[^>]*)?>\\s*\\[\\[museum-video:([a-z0-9]+(?:-[a-z0-9]+)*)\\]\\]\\s*</p>~',
                $body, $placed);
            if (count($tokens[0]) !== substr_count($body, '[[museum-video:')
                || count($tokens[0]) !== count($placed[0])) {
                throw new \RuntimeException('Invalid inline placement for video marker in published entry: '.$publicEntry->slug);
            }
            $ready = $publicEntry->videos
                ->where('status', 'published')->keyBy('code');
            foreach ($tokens[1] as $code) {
                $candidate = $ready->get($code);
                if ($candidate === null
                    || MuseumVideoUrlPolicy::safeEmbed((string)$candidate->embed_url) !== $candidate->embed_url
                    || !MuseumVideoUrlPolicy::sourceValid((string)$candidate->source_url)
                    || !$candidate->rights_confirmed
                    || mb_strlen(trim((string)$candidate->transcript)) < 60) {
                    throw new \RuntimeException('Unapproved video marker in published entry: '.$publicEntry->slug);
                }
            }
        }

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
                ...array_filter([
                    'h1' => $event->h1,
                    'seo_title' => $event->seo_title,
                    'seo_description' => $event->seo_description,
                ], static fn ($value): bool => trim((string) $value) !== ''),
                'category' => $event->category,
                'date' => $event->starts_at->format('Y-m-d'),
                'excerpt' => $event->excerpt, 'body' => $event->body,
            ];
            // A manually selected cover may be exported ONLY if the owner
            // entry is in the SAME approved public snapshot and same
            // editorial section. A withdrawn/draft entry cannot leak an
            // image into the event page, however stale the foreign key.
            $cover=$event->coverMedia;
            if ($cover!==null && $cover->entry!==null
                && $entryById->has($cover->museum_entry_id)
                && $cover->entry->museum_section_id===$event->museum_section_id
                && preg_match('/^[a-f0-9]{64}$/D',$cover->sha256)) {
                $out['cover_image'] = [
                    'src'=>'/media/'.$cover->sha256.'.webp',
                    'alt'=>$cover->alt,
                    'width'=>$cover->width,'height'=>$cover->height,
                    'caption'=>$cover->caption,
                    ...($cover->long_description!==null && trim($cover->long_description)!==''
                        ? ['long_description'=>$cover->long_description] : []),
                ];
            }
            // Section assignment exists only when specified; legacy JSON remains compatible.
            if ($event->section !== null) $out['section_slug'] = $event->section->slug;
            // Preserve stable snapshot hashes and old contracts for one-day events.
            if ($event->ends_at !== null) $out['ends_on'] = $event->ends_at->format('Y-m-d');
            $related = $publicLinks($event->relatedEntries, $entryById, $entryLink);
            if ($related !== []) $out['related_entries'] = $related;
            return $out;
        })->all();

        $entries = $publicEntries
            ->map(function (MuseumEntry $entry) use (&$mediaFiles, &$documentFiles, $mediaDir, $documentDir, $inspector,
                $entryById, $eventById, $entryLink, $eventLink, $publicLinks): array {
                $images = [];
                foreach ($entry->media as $image) {
                    // Also protect older records inserted before the new
                    // upload policy. Never export a non-compliant public alt.
                    if ($issue = MuseumAltPolicy::issue($image->alt)) {
                        throw new \RuntimeException('Public media alt policy failed; fix in private CMS: '.$image->id);
                    }
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
                        ...($image->long_description !== null && trim($image->long_description) !== ''
                            ? ['long_description' => $image->long_description] : []),
                        'width' => $image->width, 'height' => $image->height,
                    ];
                }
                // Editor inserts [[museum-video:code]] as a standalone
                // WYSIWYG paragraph. Unapproved/missing media must fail a
                // publication, never become an uncontrolled third-party iframe.
                $usedCodes = [];
                preg_match_all('/\\[\\[museum-video:([a-z0-9]+(?:-[a-z0-9]+)*)\\]\\]/D',
                    (string) $entry->body, $matches);
                foreach ($matches[1] as $code) $usedCodes[$code] = true;
                $videos = [];
                foreach ($entry->videos as $video) {
                    if ($video->status !== 'published' || !isset($usedCodes[$video->code])) continue;
                    $safe = MuseumVideoUrlPolicy::safeEmbed((string)$video->embed_url);
                    if ($safe === null || $safe !== $video->embed_url
                        || !MuseumVideoUrlPolicy::sourceValid((string)$video->source_url)
                        || !$video->rights_confirmed
                        || mb_strlen(trim((string)$video->transcript)) < 60) {
                        throw new \RuntimeException('Editorial video validation failed for material '.$entry->slug);
                    }
                    $videos[] = [
                        'code' => $video->code, 'title' => $video->title,
                        'embed_url' => $safe, 'source_url' => $video->source_url,
                        'transcript' => $video->transcript,
                    ];
                    unset($usedCodes[$video->code]);
                }
                if($usedCodes !== [] || preg_match('/\\[\\[museum-video:/D', (string)$entry->body)
                    && count($matches[0]) !== substr_count((string)$entry->body,'[[museum-video:')) {
                    throw new \RuntimeException('A video token is invalid or not approved for '.$entry->slug);
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
                'videos' => $videos,
                'documents' => $documents,
                'translations' => trim((string) $entry->title_en) !== ''
                    && trim((string) $entry->body_en) !== '' ? [
                        'en' => [
                            'title' => $entry->title_en,
                            'excerpt' => $entry->excerpt_en,
                            'body' => $entry->body_en,
                            ...($entry->h1_en !== null && trim($entry->h1_en) !== '' ? ['h1' => $entry->h1_en] : []),
                            'seo_title' => $entry->seo_title_en,
                            'seo_description' => $entry->seo_description_en,
                        ],
                    ] : null,
            ], static function ($value, $key): bool {
                if (in_array($key, ['media', 'videos', 'documents', 'related_entries', 'related_events'], true)) return count($value) > 0;
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
        // Official visitor contact facts are a single complete, approved
        // CMS-owned card. Never export draft details or split-brain mixed
        // reference/CMS values. Legacy fixture export remains unchanged.
        $visitorContacts = MuseumVisitorContacts::query()
            ->where('scope','primary')->where('status','published')->first();
        if ($visitorContacts !== null) {
            // Reapply server-side validation to records imported before the
            // current form rules, so no partial contact card is published.
            foreach (MuseumVisitorContacts::FACTS as $field) {
                if (trim((string)$visitorContacts->$field)==='') {
                    throw new \RuntimeException('Incomplete approved visitor contacts: '.$field);
                }
            }
            $data['visitor_contacts'] = collect(MuseumVisitorContacts::FACTS)
                ->mapWithKeys(static fn(string $field):array=>[$field=>$visitorContacts->$field])->all();
        }
        // Preserve the original schema for fixture parity when the seed is absent.
        // CMS-controlled navigation becomes authoritative once sections are created.
        if ($allSections->isNotEmpty()) {
            $data['sections'] = $sections;
        }
        // Fixed page metadata is optional. Do not duplicate content entry
        // SEO: entries and event pages have their own editorial owners.
        $fixedSeo = MuseumFixedPageSeo::query()->where('status', 'published')
            ->orderBy('path')->get()->mapWithKeys(static fn (MuseumFixedPageSeo $page) => [
                $page->path => array_filter([
                    'h1' => $page->h1,
                    'seo_title' => $page->seo_title,
                    'seo_description' => $page->seo_description,
                ], static fn ($value): bool => trim((string) $value) !== ''),
            ])->filter(static fn (array $values): bool => $values !== [])->all();
        if ($fixedSeo !== []) $data['fixed_page_seo'] = $fixedSeo;

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

        // Detect edits/attachment changes occurring during snapshot construction.
        // This is a second safety check, not a substitute for an immutable DB snapshot.
        try {
            app(\App\Support\MuseumExplicitApprovalGate::class)->assertUnchanged($approvedSet);
        } catch (\RuntimeException $exception) {
            $this->error('Approval gate denied export after snapshot build: '.$exception->getMessage());
            return self::FAILURE;
        }
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
