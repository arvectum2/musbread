<?php

declare(strict_types=1);

namespace App\MoonShine\Resources\MuseumFixedPageSeo\Pages;

use MoonShine\Laravel\Pages\Crud\IndexPage;
use MoonShine\UI\Fields\ID;
use MoonShine\UI\Fields\Text;

final class FixedPageSeoIndexPage extends IndexPage
{
    protected function fields(): iterable
    {
        return [
            ID::make()->sortable(),
            Text::make('Путь на сайте', 'path'),
            Text::make('SEO-заголовок', 'seo_title'),
            Text::make('H1', 'h1'),
            Text::make('Статус', 'status'),
        ];
    }
}
