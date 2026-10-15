<?php

declare(strict_types=1);

namespace App\MoonShine\Resources\MuseumEvent\Pages;

use App\MoonShine\Resources\MuseumEvent\MuseumEventResource;
use MoonShine\Laravel\Pages\Crud\IndexPage;
use MoonShine\UI\Fields\ID;
use MoonShine\UI\Fields\Text;
use MoonShine\UI\Fields\Date;

final class MuseumEventIndexPage extends IndexPage
{
    protected function fields(): iterable
    {
        return [
            ID::make()->sortable(),
            Text::make('Название', 'title'),
            Text::make('Тип', 'category'),
            Text::make('Статус', 'status'),
            Date::make('Дата', 'starts_at')->format('d.m.Y')->sortable(),
        ];
    }
}
