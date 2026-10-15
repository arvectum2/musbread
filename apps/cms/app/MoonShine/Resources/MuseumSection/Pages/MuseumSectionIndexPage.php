<?php

declare(strict_types=1);

namespace App\MoonShine\Resources\MuseumSection\Pages;

use MoonShine\Laravel\Pages\Crud\IndexPage;
use MoonShine\UI\Fields\ID;
use MoonShine\UI\Fields\Text;
use MoonShine\UI\Fields\Number;

final class MuseumSectionIndexPage extends IndexPage
{
    protected function fields(): iterable
    {
        return [
            ID::make()->sortable(),
            Text::make('Название', 'title'),
            Text::make('Slug', 'slug'),
            Text::make('Статус', 'status'),
            Number::make('Порядок', 'sort_order')->sortable(),
        ];
    }
}
