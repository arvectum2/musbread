<?php

declare(strict_types=1);

namespace App\Support;

use App\Models\MuseumEntry;

/** Stable fingerprint for one saved CMS revision and its linked assets. */
final class MuseumApprovalRevision
{
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
        sort($relations);
        sort($events);
        return hash('sha256', json_encode([
            'version' => 2,
            'model' => $attributes,
            'media' => $media,
            'documents' => $documents,
            'relations' => $relations,
            'events' => $events,
        ], JSON_THROW_ON_ERROR | JSON_UNESCAPED_UNICODE));
    }
}
