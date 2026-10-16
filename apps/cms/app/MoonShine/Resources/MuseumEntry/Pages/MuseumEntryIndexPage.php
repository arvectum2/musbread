<?php

declare(strict_types=1);

namespace App\MoonShine\Resources\MuseumEntry\Pages;

use App\Models\MuseumEntry;
use App\Models\MuseumSection;
use App\Support\MuseumEntryPublicationState;
use App\Support\MuseumSectionAccess;
use Illuminate\Database\Eloquent\Builder;
use MoonShine\Laravel\Pages\Crud\IndexPage;
use MoonShine\UI\Fields\Date;
use MoonShine\UI\Fields\ID;
use MoonShine\UI\Fields\Select;
use MoonShine\UI\Fields\Text;

final class MuseumEntryIndexPage extends IndexPage
{
    protected function fields(): iterable
    {
        return [
            ID::make()->sortable(),
            Text::make('Тип', 'type'),
            Text::make('Название', 'title')->sortable(),
            Text::make('Адрес', 'slug'),
            Text::make('Статус', 'status'),
            Text::make('Раздел', 'section.title'),
            Date::make('Публиковать с', 'published_at')->format('d.m.Y H:i')->sortable(),
            Text::make('Связанных материалов', 'editorial_related_entries_count'),
            Text::make('Событий', 'editorial_linked_events_count'),
            Text::make('Проверка', 'id')->link(
                static fn ($id): string => route('museum.content.preflight').'#entry-'.(int) $id,
                'Открыть отчёт'
            ),
            Text::make('Связи', 'id')->link(
                static fn ($id): string => route('museum.entries.relations.edit', ['entry' => $id]),
                'Настроить'
            ),
            Text::make('Предпросмотр', 'id')->link(
                static fn ($id): string => route('museum.entries.preview', ['entry' => $id]),
                'Открыть', blank: true
            ),
        ];
    }

    protected function filters(): iterable
    {
        $user = MuseumSectionAccess::user();
        $allowedIds = $user ? MuseumSectionAccess::allowedIds($user) : [];
        $sections = MuseumSection::query()->whereIn('id', $allowedIds)
            ->orderBy('title')->pluck('title', 'id')->all();
        if ($user?->isSuperUser()) $sections['unassigned'] = 'Без раздела';

        return [
            Select::make('Тип материала', 'type')->options(MuseumEntry::TYPES)->nullable(),
            Select::make('Статус редактора', 'status')
                ->options(['draft' => 'Черновик', 'published' => 'Опубликовано'])->nullable(),
            Select::make('Раздел сайта', 'museum_section_id')->options($sections)->nullable()
                ->onApply(static function (Builder $query, mixed $value): Builder {
                    if ($value === 'unassigned') return $query->whereNull('museum_section_id');
                    // Unknown/forged IDs must never expand existing ACL scope.
                    if (! ctype_digit((string) $value)) return $query->whereRaw('1=0');
                    return $query->where('museum_section_id', (int) $value);
                }),
            Select::make('Готовность к экспорту', 'publication_state')
                ->options(MuseumEntryPublicationState::OPTIONS)->nullable()
                ->onApply(static fn (Builder $query, mixed $value): Builder =>
                    MuseumEntryPublicationState::apply($query, is_string($value) ? $value : '')),
            Select::make('Наличие связей', 'link_state')
                ->options(['linked' => 'Есть связи', 'unlinked' => 'Нет связей'])->nullable()
                ->onApply(static function (Builder $query, mixed $value) use ($user): Builder {
                    if ($user === null || ! in_array($value, ['linked', 'unlinked'], true)) {
                        return $query->whereRaw('1=0');
                    }
                    $hasAccessibleRelation = static fn (Builder $builder): Builder => $builder
                        ->whereHas('relatedEntries', static fn (Builder $q) => $q->editableBy($user))
                        ->orWhereHas('linkedEvents');
                    return $value === 'linked'
                        ? $query->where($hasAccessibleRelation)
                        : $query->whereNot($hasAccessibleRelation);
                }),
        ];
    }
}
