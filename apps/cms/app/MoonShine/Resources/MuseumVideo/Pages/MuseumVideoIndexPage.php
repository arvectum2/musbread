<?php
declare(strict_types=1);
namespace App\MoonShine\Resources\MuseumVideo\Pages;
use MoonShine\Laravel\Pages\Crud\IndexPage;
use MoonShine\UI\Fields\ID;
use MoonShine\UI\Fields\Text;
final class MuseumVideoIndexPage extends IndexPage {
    protected function fields():iterable{
        return [ID::make(),Text::make('Код маркера','code'),
            Text::make('Заголовок','title'),Text::make('Статус','status')];
    }
}
