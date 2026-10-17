<?php
declare(strict_types=1);
namespace App\MoonShine\Resources\MuseumVisitorContacts\Pages;
use MoonShine\Laravel\Pages\Crud\IndexPage;
use MoonShine\UI\Fields\ID;
use MoonShine\UI\Fields\Text;
final class VisitorContactsIndexPage extends IndexPage {
    protected function fields():iterable {
        return [ID::make(),Text::make('Карточка','scope'),
            Text::make('Адрес музея','address'),Text::make('Статус','status')];
    }
}
