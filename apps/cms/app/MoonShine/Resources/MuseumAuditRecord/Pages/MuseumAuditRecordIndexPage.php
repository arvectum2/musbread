<?php

declare(strict_types=1);

namespace App\MoonShine\Resources\MuseumAuditRecord\Pages;

use MoonShine\Laravel\Pages\Crud\IndexPage;
use MoonShine\UI\Fields\ID;
use MoonShine\UI\Fields\Text;
use MoonShine\UI\Fields\Date;

final class MuseumAuditRecordIndexPage extends IndexPage
{
    protected function fields(): iterable
    {
        return [
            ID::make()->sortable(),
            Text::make('Объект', 'subject_type'),
            Text::make('ID объекта', 'subject_id'),
            Text::make('Действие', 'action'),
            Text::make('ID редактора', 'actor_id'),
            Date::make('Дата и время', 'created_at')->withTime(),
        ];
    }
}
