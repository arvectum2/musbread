<?php
declare(strict_types=1);
namespace App\MoonShine\Resources\MuseumInboundRequest\Pages;
use MoonShine\Laravel\Pages\Crud\DetailPage;
use MoonShine\UI\Fields\ID;
use MoonShine\UI\Fields\Text;
use MoonShine\UI\Fields\Textarea;
final class InboxDetailPage extends DetailPage {
    protected function fields(): iterable {
        return [ID::make(),Text::make('Номер','external_id'),
            Text::make('Тип','kind'),Text::make('Имя','visitor_name'),
            Text::make('Электронная почта','visitor_email'),
            Textarea::make('Текст','visitor_message'),
            Text::make('Дата экскурсии','visitor_date'),
            Text::make('Группа','visitor_group')];
    }
}
