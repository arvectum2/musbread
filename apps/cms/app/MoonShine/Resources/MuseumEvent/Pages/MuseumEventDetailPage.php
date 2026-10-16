<?php

declare(strict_types=1);

namespace App\MoonShine\Resources\MuseumEvent\Pages;

use MoonShine\Laravel\Pages\Crud\DetailPage;
use MoonShine\UI\Fields\ID;
use MoonShine\UI\Fields\Text;
use MoonShine\UI\Fields\Textarea;
use MoonShine\UI\Fields\Date;

final class MuseumEventDetailPage extends DetailPage
{
    protected function fields(): iterable
    {
        return [
            ID::make(), Text::make('Название', 'title'),
            Text::make('Тип', 'category'), Date::make('Начало', 'starts_at'), Date::make('Окончание', 'ends_at'),
            Text::make('Статус', 'status'),
            Textarea::make('Описание', 'body'),
        ];
    }
}
