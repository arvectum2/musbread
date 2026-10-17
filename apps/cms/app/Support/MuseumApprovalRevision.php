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
        $media = $entry->media()->get(['id', 'sha256', 'alt', 'caption'])
            ->map(static fn ($row) => [$row->id, $row->sha256, $row->alt, $row->caption])->all();
        $documents = $entry->documents()->get(['id', 'sha256', 'file_type'])
            ->map(static fn ($row) => [$row->id, $row->sha256, $row->file_type])->all();
        $relations = $entry->relatedEntries()->pluck('museum_entries.id')->all();
        $events = $entry->linkedEvents()->pluck('museum_events.id')->all();
        sort($media);
        sort($documents);
        sort($relations);
        sort($events);
        return hash('sha256', json_encode([
            'version' => 1,
            'model' => $attributes,
            'media' => $media,
            'documents' => $documents,
            'relations' => $relations,
            'events' => $events,
        ], JSON_THROW_ON_ERROR | JSON_UNESCAPED_UNICODE));
    }
}
