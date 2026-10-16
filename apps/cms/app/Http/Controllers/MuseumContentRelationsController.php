<?php

declare(strict_types=1);

namespace App\Http\Controllers;

use App\Models\MuseumEntry;
use App\Models\MuseumEvent;
use App\Support\MuseumSectionAccess;
use Illuminate\Http\RedirectResponse;
use Illuminate\Http\Request;
use Illuminate\Http\Response;
use Illuminate\Support\Facades\DB;
use Illuminate\Validation\Rule;
use Illuminate\Validation\ValidationException;

/** Private editor UI for explicit links, never exposed through the public site. */
final class MuseumContentRelationsController extends Controller
{
    private function editableEntry(int|string $id): MuseumEntry
    {
        $actor = MuseumSectionAccess::user();
        if ($actor === null || ! ctype_digit((string) $id)) abort(404);

        return MuseumEntry::query()->editableBy($actor)->findOrFail($id);
    }

    public function edit(string $entry): Response
    {
        $record = $this->editableEntry($entry);
        $actor = MuseumSectionAccess::user();

        return response()->view('entries.relations', [
            'entry' => $record,
            'editable' => MuseumEntry::query()->editableBy($actor)
                ->whereKeyNot($record->getKey())->orderBy('title')->get(['id', 'title', 'type']),
            // Events currently have CMS-wide Editor access (no section ACL).
            'events' => MuseumEvent::query()->orderBy('title')->get(['id', 'title', 'category']),
            'selectedEntries' => $record->relatedEntries()->pluck('museum_entries.id')->all(),
            'selectedEvents' => $record->linkedEvents()->pluck('museum_events.id')->all(),
        ], 200, [
            'Cache-Control' => 'private, no-store, max-age=0',
            'X-Robots-Tag' => 'noindex, nofollow, noarchive',
            'X-Frame-Options' => 'DENY',
            'Content-Security-Policy' => "default-src 'none'; style-src 'unsafe-inline'; "
                ."form-action 'self'; base-uri 'none'; frame-ancestors 'none'",
        ]);
    }

    public function update(Request $request, string $entry): RedirectResponse
    {
        $record = $this->editableEntry($entry);
        $data = $request->validate([
            'related_entry_ids' => ['sometimes', 'array'],
            'related_entry_ids.*' => ['integer', 'distinct', Rule::exists('museum_entries', 'id')],
            'related_event_ids' => ['sometimes', 'array'],
            'related_event_ids.*' => ['integer', 'distinct', Rule::exists('museum_events', 'id')],
        ]);
        $entryIds = array_map('intval', $data['related_entry_ids'] ?? []);
        $eventIds = array_map('intval', $data['related_event_ids'] ?? []);
        $actor = MuseumSectionAccess::user();
        // Enforce target grants: a source editor must not reveal other sections'
        // unpublished records in the relationship UI or write hidden link IDs.
        if (in_array($record->id, $entryIds, true)
            || MuseumEntry::query()->editableBy($actor)->whereKey($entryIds)->count() !== count($entryIds)) {
            throw ValidationException::withMessages([
                'related_entry_ids' => 'Нельзя связать материал с собой или с чужим разделом.',
            ]);
        }
        DB::transaction(static function () use ($record, $entryIds, $eventIds): void {
            $record->relatedEntries()->sync($entryIds);
            $record->linkedEvents()->sync($eventIds);
        });

        return redirect()->route('museum.entries.relations.edit', ['entry' => $record->id])
            ->with('status', 'Связи сохранены. В публичную версию попадут только опубликованные объекты.');
    }
}
