<?php

declare(strict_types=1);

namespace App\MoonShine\Resources\MuseumEntry\Pages;

use MoonShine\Laravel\Pages\Crud\DetailPage;
use MoonShine\UI\Fields\ID;
use MoonShine\UI\Fields\Text;
use MoonShine\UI\Fields\Textarea;

final class MuseumEntryDetailPage extends DetailPage
{
    protected function fields(): iterable
    {
        return [
            ID::make(),
            Text::make('Тип', 'type'), Text::make('Название', 'title'),
            Text::make('Адрес', 'slug'), Text::make('Статус', 'status'),
            Textarea::make('Основной текст', 'body'),
        ];
    }
}
