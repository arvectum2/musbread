<?php

declare(strict_types=1);

namespace App\MoonShine\Resources\MuseumRequestTransition\Pages;

use MoonShine\Laravel\Pages\Crud\IndexPage;
use MoonShine\UI\Fields\Date;
use MoonShine\UI\Fields\ID;
use MoonShine\UI\Fields\Text;

final class MuseumRequestTransitionIndexPage extends IndexPage
{
    protected function fields(): iterable
    {
        return [
            ID::make()->sortable(),
            Text::make('Обращение ID', 'museum_request_id'),
            Text::make('Прежний статус', 'from_status'),
            Text::make('Новый статус', 'to_status'),
            Text::make('Исполнитель ID', 'actor_id'),
            Date::make('Время', 'created_at')->withTime()->sortable(),
        ];
    }
}
