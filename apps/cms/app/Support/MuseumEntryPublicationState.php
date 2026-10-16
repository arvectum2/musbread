<?php

declare(strict_types=1);

namespace App\Support;

use App\Models\MuseumSection;
use Illuminate\Database\Eloquent\Builder;

/** Read-only review states, not an additional publication approval mechanism. */
final class MuseumEntryPublicationState
{
    public const OPTIONS = [
        'draft' => 'Черновик',
        'scheduled' => 'Ожидает даты публикации',
        'blocked' => 'Скрыто разделом или родителем',
        'ready' => 'Готово к следующей выгрузке',
    ];

    /** Same ancestor-publication semantics as museum:export, with no personal fields. */
    public static function publishedSectionIds(): array
    {
        $all = MuseumSection::query()->get(['id', 'parent_id', 'status']);
        $byId = $all->keyBy('id');
        return $all->filter(static function (MuseumSection $section) use ($byId): bool {
            $seen = [];
            $node = $section;
            while ($node !== null) {
                if ($node->status !== 'published' || isset($seen[$node->id])) return false;
                $seen[$node->id] = true;
                if ($node->parent_id !== null && ! $byId->has($node->parent_id)) return false;
                $node = $node->parent_id === null ? null : $byId->get($node->parent_id);
            }
            return true;
        })->modelKeys();
    }

    /** Build SQL predicates instead of fetching/filtering private records in PHP. */
    public static function apply(Builder $query, string $state): Builder
    {
        if (! array_key_exists($state, self::OPTIONS)) return $query->whereRaw('1 = 0');
        if ($state === 'draft') return $query->where('status', 'draft');

        $query->where('status', 'published');
        if ($state === 'scheduled') {
            return $query->where(static fn (Builder $q) => $q
                ->whereNull('published_at')->orWhere('published_at', '>', now()));
        }

        $query->whereNotNull('published_at')->where('published_at', '<=', now());
        $ids = self::publishedSectionIds();
        if ($state === 'ready') {
            return $query->where(static fn (Builder $q) => $q
                ->whereNull('museum_section_id')->when($ids !== [],
                    static fn (Builder $builder) => $builder->orWhereIn('museum_section_id', $ids)));
        }

        // Excludes null (unassigned) records: legacy content with null section
        // remains eligible for publication under the existing export contract.
        return $query->whereNotNull('museum_section_id')
            ->when($ids !== [], static fn (Builder $q) => $q->whereNotIn('museum_section_id', $ids));
    }
}
