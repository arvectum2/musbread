<?php

declare(strict_types=1);

namespace App\MoonShine\Resources\MuseumRequest\Pages;

use MoonShine\Laravel\Pages\Crud\IndexPage;
use MoonShine\UI\Fields\Date;
use MoonShine\UI\Fields\ID;
use MoonShine\UI\Fields\Text;

final class MuseumRequestIndexPage extends IndexPage
{
    protected function fields(): iterable
    {
        return [
            ID::make()->sortable(),
            Text::make('Номер', 'reference'),
            Text::make('Тип', 'type'),
            Text::make('Тема', 'topic'),
            Text::make('Статус', 'status'),
            Text::make('Раздел ID', 'museum_section_id'),
            Text::make('Ответственный ID', 'assigned_to_id'),
            Date::make('Создано', 'created_at')->format('d.m.Y H:i')->sortable(),
        ];
    }
}
