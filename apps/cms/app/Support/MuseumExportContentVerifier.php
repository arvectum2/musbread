<?php

declare(strict_types=1);

namespace App\Support;

use App\Models\MuseumContentApproval;
use App\Models\MuseumEntry;
use App\Models\MuseumEvent;
use App\Models\MuseumExportContentProof;
use App\Models\MuseumPublicationRun;
use App\Models\MuseumSection;
use Illuminate\Support\Facades\DB;
use RuntimeException;

/**
 * Read-only verification of actual snapshot bytes against approved CMS rows.
 *
 * Strictly private: never embeds CMS IDs or approval hashes in schema-v1
 * public JSON/manifest. Rejects duplicate/missing/extra rows, mismatched core
 * serialized content, stale approval and tampered/unavailable binary assets.
 * The source serializer remains the final authority for optional fields.
 */
final class MuseumExportContentVerifier
{
    public function verify(
        MuseumPublicationRun $run,
        string $snapshotPath,
        string $manifestPath,
        string $mediaDir,
        string $documentDir
    ): void {
        if (! config('museum.editorial_approval_queue', false)) {
            return; // Legacy precontract jobs have no explicit approvals.
        }
        $this->mediaDir = $mediaDir;
        $this->documentDir = $documentDir;
        if (! is_file($snapshotPath) || ! is_file($manifestPath)) {
            throw new RuntimeException('Export content proof requires both finished JSON files');
        }
        $raw = file_get_contents($snapshotPath);
        $manifestRaw = file_get_contents($manifestPath);
        if ($raw === false || $manifestRaw === false) {
            throw new RuntimeException('Cannot read exported content proof sources');
        }
        $snapshot = json_decode($raw, true, 512, JSON_THROW_ON_ERROR);
        $manifest = json_decode($manifestRaw, true, 512, JSON_THROW_ON_ERROR);
        if (! is_array($snapshot) || ! is_array($manifest)
            || ($snapshot['schema_version'] ?? null) !== 1
            || ($manifest['schema_version'] ?? null) !== 1) {
            throw new RuntimeException('Unsupported exported content proof schema');
        }

        // Approval mode explicitly disallows CMS-owned site-wide metadata
        // until those fields have their own editorial approval. Never allow
        // an injected top-level collection or tampered prototype identity to
        // be laundered through a freshly rehashed manifest.
        if (array_diff(array_keys($snapshot),
            ['schema_version','site','entries','events','sections']) !== []
            || ! $this->matchesJson($snapshot['site'] ?? null, [
                'name' => 'Музей Хлеба',
                'subtitle' => 'Демонстрационная версия · концепция не утверждена',
                'description' => 'Предконтрактный прототип информационного сайта музея.',
            ])) {
            throw new RuntimeException('Export contains unapproved top-level site data');
        }

        $hash = hash('sha256', $raw);
        $manifestFiles = $manifest['files'] ?? null;
        if (! is_array($manifestFiles)
            || ($manifestFiles['published.json']['sha256'] ?? null) !== $hash
            || ($manifestFiles['published.json']['bytes'] ?? null) !== strlen($raw)) {
            throw new RuntimeException('Manifest does not bind actual snapshot bytes');
        }

        $assets = [];
        foreach (['entries','events','sections'] as $group) {
            if (! is_array($snapshot[$group] ?? ($group === 'sections' ? [] : null))
                || ! array_is_list($snapshot[$group] ?? [])) {
                throw new RuntimeException('Invalid snapshot content collection');
            }
        }

        $allowedSectionIds = MuseumEntryPublicationState::publishedSectionIds();
        $expectedGroups = [
            'entry' => [
                MuseumEntry::query()->public()->with(['section'])
                    ->get()->filter(static fn ($m) => $m->museum_section_id === null
                        || in_array($m->museum_section_id, $allowedSectionIds, true)),
                'entries',
            ],
            'event' => [
                MuseumEvent::query()->public()->with(['section'])
                    ->get()->filter(static fn ($m) => $m->museum_section_id === null
                        || in_array($m->museum_section_id, $allowedSectionIds, true)),
                'events',
            ],
            'section' => [
                MuseumPublishedSections::filter(MuseumSection::all()),
                'sections',
            ],
        ];
        $serializer = app(MuseumSnapshotSerializer::class);
        // Use the SAME public-and-visible subject inventory for independent
        // cross-reference verification. A link cannot leak a draft, expired or
        // ancestor-blocked target even if the attacker's manifest is rehashed.
        $publicEntryIds = array_fill_keys(
            $expectedGroups['entry'][0]->pluck('id')->all(), true
        );
        $publicEventIds = array_fill_keys(
            $expectedGroups['event'][0]->pluck('id')->all(), true
        );
        $evidence = [];
        foreach ($expectedGroups as $kind => [$records, $groupName]) {
            $index = [];
            foreach ($snapshot[$groupName] ?? [] as $item) {
                if (! is_array($item)) throw new RuntimeException('Malformed exported content record');
                $identity = $this->identity($kind, $item);
                if (isset($index[$identity])) throw new RuntimeException('Duplicate exported content identity');
                $index[$identity] = $item;
                $this->collectAssets($kind, $item, $assets);
            }
            if (count($records) !== count($index)) {
                throw new RuntimeException('Approved subject count differs from actual export rows');
            }
            foreach ($records as $subject) {
                $identity = $kind === 'entry' ? $subject->type.':'.$subject->slug : $subject->slug;
                $row = $index[$identity] ?? null;
                if ($row === null) throw new RuntimeException('Approved CMS subject absent from export');
                $this->checkCoreFields(
                    $kind, $subject, $row, $publicEntryIds, $publicEventIds
                );

                $revision = MuseumApprovalRevision::forSubject($subject);
                $key = match ($kind) {
                    'entry' => 'museum_entry_id',
                    'event' => 'museum_event_id',
                    'section' => 'museum_section_id',
                };
                $approval = MuseumContentApproval::query()
                    ->where($key, $subject->id)
                    ->where('revision_sha256', $revision)
                    ->where('dispatch_status', 'queued')
                    ->first();
                if ($approval === null) throw new RuntimeException('Exported content lacks current explicit approval');
                $evidence[] = [
                    'publication_run_id' => $run->id,
                    'approval_id' => $approval->id,
                    'subject_kind' => $kind,
                    'subject_id' => $subject->id,
                    'revision_sha256' => $revision,
                    'snapshot_sha256' => $hash,
                    'export_record_sha256' => hash('sha256', $serializer->encode($row)),
                ];
                unset($index[$identity]);
            }
            if ($index !== []) throw new RuntimeException('Unapproved extra content row in snapshot');
        }

        if (count($assets) + 1 !== count($manifestFiles)
            || count($snapshot['entries']) !== ($manifest['entry_count'] ?? null)
            || count($snapshot['events']) !== ($manifest['event_count'] ?? null)
            || (isset($snapshot['sections']) && count($snapshot['sections']) !== ($manifest['section_count'] ?? null))) {
            throw new RuntimeException('Manifest inventory differs from exported content');
        }
        foreach ($assets as $name => $directory) {
            $parts = explode('/', $name, 2);
            $file = $parts[1] ?? '';
            $expectedDigest = substr($file, 0, 64);
            $path = rtrim($directory, '/').'/'.$file;
            if (! preg_match('/^[a-f0-9]{64}\.(?:webp|pdf|docx|xlsx)$/D', $file)
                || ! is_file($path) || is_link($path)
                || ($manifestFiles[$name]['sha256'] ?? null) !== $expectedDigest
                || ($manifestFiles[$name]['bytes'] ?? null) !== filesize($path)
                || hash_file('sha256', $path) !== $expectedDigest) {
                throw new RuntimeException('Exported binary asset missing or mismatched manifest');
            }
        }
        // Commit one coherent immutable proof set. The run is marked succeeded
        // only after these rows are written; exceptions roll this transaction back.
        DB::transaction(static function () use ($run, $evidence, $hash, $manifestRaw): void {
            MuseumExportContentProof::query()->where('publication_run_id', $run->id)->delete();
            if ($evidence !== []) MuseumExportContentProof::insert($evidence);
            $run->update([
                'content_proof_count' => count($evidence),
                'content_verified_at' => now('UTC'),
                'manifest_sha256' => hash('sha256', $manifestRaw),
                'snapshot_sha256' => $hash,
            ]);
        });
    }

    private function matchesJson($actual, $expected): bool
    {
        // The canonical exporter sorts object keys in JSON; decoded arrays
        // have that order, whereas the PHP model projection follows its own
        // insertion order. Compare semantic canonical JSON, not PHP === order.
        return app(MuseumSnapshotSerializer::class)->encode(['v' => $actual])
            === app(MuseumSnapshotSerializer::class)->encode(['v' => $expected]);
    }

    private function identity(string $kind, array $row): string
    {
        $slug = $row['slug'] ?? null;
        $type = $row['type'] ?? null;
        if (! is_string($slug) || ! preg_match('/^[a-z0-9]+(?:-[a-z0-9]+)*$/D', $slug)
            || ($kind === 'entry' && (! is_string($type) || ! isset(MuseumEntry::TYPES[$type])))) {
            throw new RuntimeException('Unsafe exported content identity');
        }
        return $kind === 'entry' ? $type.':'.$slug : $slug;
    }

    /**
     * @param array<int,bool> $publicEntryIds
     * @param array<int,bool> $publicEventIds
     */
    private function checkCoreFields(
        string $kind, $model, array $row,
        array $publicEntryIds, array $publicEventIds
    ): void {
        // These allowlists mirror only the PUBLIC schema-v1 serializer.
        // No private CMS IDs, author emails, non-exported fields or injected
        // arbitrary HTML properties may silently pass as an approved row.
        $allowed = match ($kind) {
            'entry' => ['type','slug','title','h1','parent_slug','section_slug',
                'excerpt','body','seo_title','seo_description','sort_order',
                'related_entries','related_events','media','videos',
                'documents','translations'],
            'event' => ['slug','title','h1','seo_title','seo_description',
                'category','date','excerpt','body','cover_image','section_slug',
                'ends_on','related_entries'],
            'section' => ['slug','title','parent_slug','sort_order','legacy_path',
                'h1','seo_title','seo_description'],
        };
        if (array_diff(array_keys($row), $allowed) !== []) {
            throw new RuntimeException('Export contains unexpected public-schema fields');
        }
        $fields = match ($kind) {
            'entry' => ['type','slug','title','h1','parent_slug','excerpt','body',
                'seo_title','seo_description','sort_order'],
            'event' => ['slug','title','h1','excerpt','body','seo_title','seo_description','category'],
            'section' => ['slug','title','h1','seo_title','seo_description','sort_order','legacy_path'],
        };
        foreach ($fields as $field) {
            $value = $model->getAttribute($field);
            // The export intentionally omits some empty optionals, but the
            // actual populated values must always match the approved CMS source.
            if ($kind !== 'entry' && in_array($field, ['h1','seo_title','seo_description'], true)
                && trim((string) $value) === '') {
                if (array_key_exists($field, $row) && trim((string) $row[$field]) !== '') {
                    throw new RuntimeException('Export contains unapproved optional value');
                }
                continue;
            }
            if (($row[$field] ?? null) !== $value) {
                throw new RuntimeException('Exported field does not match approved CMS source: '.$field);
            }
        }
        if ($kind === 'entry') {
            // Confirm each referenced attachment's editorial metadata, not
            // just its binary SHA. The approval revision includes changes
            // to captions, alt, accessibility and approved document HTML.
            $expectedMedia = [];
            foreach ($model->media as $image) {
                if ($image->source_rights_pending) continue;
                $expectedMedia[] = [
                    'src'=>'/media/'.$image->sha256.'.webp',
                    'alt'=>$image->alt, 'caption'=>$image->caption,
                    ...($image->long_description !== null && trim($image->long_description) !== ''
                        ? ['long_description'=>$image->long_description] : []),
                    'width'=>$image->width, 'height'=>$image->height,
                ];
            }
            if (! $this->matchesJson(($row['media'] ?? []), $expectedMedia)) {
                throw new RuntimeException('Exported media metadata differs from approved CMS source');
            }
            $expectedDocuments = [];
            foreach ($model->documents as $document) {
                $expectedDocuments[] = [
                    'href'=>'/documents/'.$document->sha256.'.'.$document->file_type,
                    'label'=>$document->label, 'format'=>$document->file_type,
                    'size_bytes'=>$document->size_bytes,
                    'accessibility_reviewed'=>$document->accessibility_reviewed,
                    'accessibility_note'=>$document->accessibility_reviewed
                        ? $document->accessibility_note : null,
                    ...($document->accessible_edition_sha256 !== null
                        ? ['accessible_html'=>$document->accessible_html] : []),
                ];
            }
            if (! $this->matchesJson(($row['documents'] ?? []), $expectedDocuments)) {
                throw new RuntimeException('Exported document metadata differs from approved CMS source');
            }
            $expectedTranslations = null;
            if (trim((string) $model->title_en) !== '' && trim((string) $model->body_en) !== '') {
                $expectedTranslations = ['en'=>[
                    'title'=>$model->title_en, 'excerpt'=>$model->excerpt_en,
                    'body'=>$model->body_en,
                    ...($model->h1_en !== null && trim($model->h1_en) !== ''
                        ? ['h1'=>$model->h1_en] : []),
                    'seo_title'=>$model->seo_title_en,
                    'seo_description'=>$model->seo_description_en,
                ]];
            }
            if (! $this->matchesJson(($row['translations'] ?? null), $expectedTranslations)) {
                throw new RuntimeException('Exported translation differs from approved CMS source');
            }
            $usedCodes = [];
            preg_match_all('/\\[\\[museum-video:([a-z0-9]+(?:-[a-z0-9]+)*)\\]\\]/D',
                (string) $model->body, $matches);
            foreach ($matches[1] as $code) $usedCodes[$code] = true;
            $expectedVideos = [];
            foreach ($model->videos as $video) {
                if ($video->status !== 'published' || ! isset($usedCodes[$video->code])) continue;
                $expectedVideos[] = [
                    'code'=>$video->code, 'title'=>$video->title,
                    'embed_url'=>$video->embed_url, 'source_url'=>$video->source_url,
                    'transcript'=>$video->transcript,
                ];
            }
            if (! $this->matchesJson(($row['videos'] ?? []), $expectedVideos)) {
                throw new RuntimeException('Exported video metadata differs from approved CMS source');
            }

            // Independently rebuild the exporter-facing links from the
            // exact approved public target set, using stable title/ID order.
            // A harmless change to a linked target's title MUST change its
            // exported link and invalidate the original approval fingerprint.
            $related = $model->relatedEntries
                ->filter(static fn ($target) => isset($publicEntryIds[$target->id]))
                ->sortBy(static fn ($target) => $target->title.'|'.$target->id)
                ->map(static fn ($target) => self::entryLink($target))
                ->filter()->values()->all();
            if (! $this->matchesJson(($row['related_entries'] ?? []), $related)) {
                throw new RuntimeException('Exported related entry links differ from approved CMS source');
            }
            $events = $model->linkedEvents
                ->filter(static fn ($event) => isset($publicEventIds[$event->id]))
                ->sortBy(static fn ($event) => $event->title.'|'.$event->id)
                ->map(static fn ($event) => self::eventLink($event))
                ->filter()->values()->all();
            if (! $this->matchesJson(($row['related_events'] ?? []), $events)) {
                throw new RuntimeException('Exported related event links differ from approved CMS source');
            }
        }
        if ($kind === 'event') {
            $related = $model->relatedEntries
                ->filter(static fn ($target) => isset($publicEntryIds[$target->id]))
                ->sortBy(static fn ($target) => $target->title.'|'.$target->id)
                ->map(static fn ($target) => self::entryLink($target))
                ->filter()->values()->all();
            if (! $this->matchesJson(($row['related_entries'] ?? []), $related)) {
                throw new RuntimeException('Exported event related links differ from approved CMS source');
            }
            $cover = $model->coverMedia;
            $expectedCover = null;
            if ($cover !== null && ! $cover->source_rights_pending
                && $cover->entry !== null
                && isset($publicEntryIds[$cover->museum_entry_id])
                && $cover->entry->museum_section_id === $model->museum_section_id
                && preg_match('/^[a-f0-9]{64}$/D', (string) $cover->sha256)) {
                $expectedCover = [
                    'src'=>'/media/'.$cover->sha256.'.webp',
                    'alt'=>$cover->alt,
                    'width'=>$cover->width,
                    'height'=>$cover->height,
                    'caption'=>$cover->caption,
                    ...($cover->long_description !== null
                        && trim($cover->long_description) !== ''
                        ? ['long_description'=>$cover->long_description] : []),
                ];
            }
            if (! $this->matchesJson(($row['cover_image'] ?? null), $expectedCover)) {
                throw new RuntimeException('Exported event cover differs from approved CMS source');
            }
            if (($row['date'] ?? null) !== $model->starts_at?->format('Y-m-d')
                || (($row['ends_on'] ?? null) !== $model->ends_at?->format('Y-m-d'))) {
                throw new RuntimeException('Exported event dates differ from approved CMS source');
            }
        }
        if ($kind !== 'section') {
            if (($row['section_slug'] ?? null) !== $model->section?->slug) {
                throw new RuntimeException('Exported section assignment differs from approved CMS source');
            }
        } elseif (($row['parent_slug'] ?? null) !== $model->parent?->slug) {
            throw new RuntimeException('Exported section parent differs from approved CMS source');
        }
    }

    private static function entryLink(MuseumEntry $entry): ?array
    {
        $prefix = [
            'page'=>'museum', 'news'=>'news', 'excursion'=>'excursions',
            'exhibition'=>'exhibitions', 'document'=>'documents',
        ][$entry->type] ?? null;
        if ($prefix === null
            || ! preg_match('/^[a-z0-9]+(?:-[a-z0-9]+)*$/D', $entry->slug)) {
            return null;
        }
        return [
            'type'=>$entry->type, 'title'=>$entry->title,
            'href'=>'/'.$prefix.'/'.$entry->slug.'/',
        ];
    }

    private static function eventLink(MuseumEvent $event): ?array
    {
        if (! preg_match('/^[a-z0-9]+(?:-[a-z0-9]+)*$/D', $event->slug)) {
            return null;
        }
        return ['title'=>$event->title,'href'=>'/events/'.$event->slug.'/'];
    }

    private function collectAssets(string $kind, array $row, array &$assets): void
    {
        if ($kind === 'entry') {
            foreach ($row['media'] ?? [] as $media) {
                $this->addAsset($assets, $media['src'] ?? null, 'media');
            }
            foreach ($row['documents'] ?? [] as $document) {
                $this->addAsset($assets, $document['href'] ?? null, 'documents');
            }
        }
        if ($kind === 'event' && isset($row['cover_image'])) {
            $this->addAsset($assets, $row['cover_image']['src'] ?? null, 'media');
        }
    }

    private function addAsset(array &$assets, $path, string $kind): void
    {
        if (! is_string($path)
            || ! preg_match('~^/'.preg_quote($kind, '~').'/[a-f0-9]{64}\.'
                .($kind === 'media' ? 'webp' : '(?:pdf|docx|xlsx)').'$~D', $path)) {
            throw new RuntimeException('Unsafe asset reference in exported content');
        }
        $assets[ltrim($path, '/')] = $kind === 'media'
            ? $this->mediaDir : $this->documentDir;
    }

    private string $mediaDir = '';
    private string $documentDir = '';
}
