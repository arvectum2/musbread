<?php
declare(strict_types=1);
namespace App\MoonShine\Resources\MuseumInboundRequest\Pages;
use MoonShine\Laravel\Pages\Crud\IndexPage;
use MoonShine\UI\Fields\ID;
use MoonShine\UI\Fields\Text;
use MoonShine\UI\Fields\Date;
final class InboxIndexPage extends IndexPage {
    protected function fields(): iterable {
        return [ID::make()->sortable(),Text::make('Тип','kind'),
            Text::make('Номер','external_id'),
            Date::make('Получено','received_at')->withTime()->sortable()];
    }
}
