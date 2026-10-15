<?php

declare(strict_types=1);

namespace App\MoonShine\Resources\MuseumEntry\Pages;

use MoonShine\Laravel\Pages\Crud\IndexPage;
use MoonShine\UI\Fields\ID;
use MoonShine\UI\Fields\Text;

final class MuseumEntryIndexPage extends IndexPage
{
    protected function fields(): iterable
    {
        return [
            ID::make()->sortable(),
            Text::make('Тип', 'type'),
            Text::make('Название', 'title'),
            Text::make('Адрес', 'slug'),
            Text::make('Статус', 'status'),
            Text::make('Раздел ID', 'museum_section_id'),
        ];
    }
}
