<?php

declare(strict_types=1);

namespace App\Support;

use App\Models\MuseumEntry;
use App\Models\MuseumEvent;
use App\Models\MuseumSection;
use Illuminate\Database\Eloquent\Model;
use InvalidArgumentException;

/** Stable fingerprint for one saved CMS revision and its linked assets. */
final class MuseumApprovalRevision
{
    /** Same editorial decision and hash contract for the three public content owners. */
    public static function forSubject(Model $subject): string
    {
        if ($subject instanceof MuseumEntry) return self::fingerprint($subject);
        if (! $subject instanceof MuseumEvent && ! $subject instanceof MuseumSection) {
            throw new InvalidArgumentException('Unsupported editorial approval subject');
        }
        $attrs = $subject->getAttributes();
        ksort($attrs);
        $extra = [];
        if ($subject instanceof MuseumEvent) {
            $extra['related_entry_ids'] = $subject->relatedEntries()
                ->pluck('museum_entries.id')->sort()->values()->all();
            $cover = $subject->coverMedia;
            if ($cover !== null) {
                $extra['cover_media'] = $cover->getAttributes();
                ksort($extra['cover_media']);
            }
        }
        return hash('sha256', json_encode([
            'version' => 1,
            'type' => $subject instanceof MuseumEvent ? 'event' : 'section',
            'model' => $attrs,
            'dependencies' => $extra,
        ], JSON_THROW_ON_ERROR | JSON_UNESCAPED_UNICODE));
    }

    public static function fingerprint(MuseumEntry $entry): string
    {
        // Raw saved fields, NOT "published_at" as an approval clock.
        // The associations can change without touching entry.updated_at.
        $attributes = $entry->getAttributes();
        ksort($attributes);
        // Include ALL persisted asset metadata affecting public delivery, not
        // only the binary checksum. Captions, detailed alt, document labels,
        // accessibility notes, file paths and timestamps also need re-approval.
        $media = $entry->media()->orderBy('id')->get()
            ->map(static function ($row): array {
                $attrs = $row->getAttributes();
                ksort($attrs);
                return $attrs;
            })->all();
        // Video metadata is approval-sensitive: switching a URL, captions,
        // rights or publication status invalidates any earlier editorial vote.
        $videos = $entry->videos()->orderBy('id')->get()
            ->map(static function ($row): array {
                $attrs = $row->getAttributes();
                ksort($attrs);
                return $attrs;
            })->all();
        $documents = $entry->documents()->orderBy('id')->get()
            ->map(static function ($row): array {
                $attrs = $row->getAttributes();
                ksort($attrs);
                return $attrs;
            })->all();
        $relations = $entry->relatedEntries()->pluck('museum_entries.id')->all();
        $events = $entry->linkedEvents()->pluck('museum_events.id')->all();
        sort($media);
        sort($documents);
        sort($videos);
        sort($relations);
        sort($events);
        return hash('sha256', json_encode([
            'version' => 2,
            'model' => $attributes,
            'media' => $media,
            'documents' => $documents,
            'videos' => $videos,
            'relations' => $relations,
            'events' => $events,
        ], JSON_THROW_ON_ERROR | JSON_UNESCAPED_UNICODE));
    }
}
