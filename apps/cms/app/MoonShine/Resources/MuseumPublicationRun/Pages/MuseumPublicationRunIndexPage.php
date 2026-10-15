<?php

declare(strict_types=1);

namespace App\MoonShine\Resources\MuseumPublicationRun\Pages;

use MoonShine\Laravel\Pages\Crud\IndexPage;
use MoonShine\UI\Fields\Date;
use MoonShine\UI\Fields\ID;
use MoonShine\UI\Fields\Text;

final class MuseumPublicationRunIndexPage extends IndexPage
{
    protected function fields(): iterable
    {
        return [
            ID::make()->sortable(),
            Text::make('Статус', 'status'),
            Text::make('Попыток', 'attempts'),
            Text::make('Контрольная сумма SHA-256', 'snapshot_sha256'),
            Text::make('Тип ошибки', 'error_type'),
            Date::make('Начало', 'started_at')->withTime(),
            Date::make('Окончание', 'finished_at')->withTime(),
        ];
    }
}
