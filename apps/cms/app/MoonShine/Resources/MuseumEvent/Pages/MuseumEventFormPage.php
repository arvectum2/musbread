<?php

declare(strict_types=1);

namespace App\MoonShine\Resources\MuseumEvent\Pages;

use App\MoonShine\Resources\MuseumEvent\MuseumEventResource;
use MoonShine\Laravel\Pages\Crud\FormPage;
use MoonShine\UI\Components\Layout\Box;
use MoonShine\UI\Fields\ID;
use MoonShine\UI\Fields\Text;
use MoonShine\UI\Fields\Textarea;
use MoonShine\UI\Fields\Date;
use MoonShine\UI\Fields\Select;
use MoonShine\Contracts\Core\TypeCasts\DataWrapperContract;

final class MuseumEventFormPage extends FormPage
{
    protected function fields(): iterable
    {
        return [
            Box::make([
                ID::make(),
                Text::make('Название', 'title')->required(),
                Text::make('URL (латиница, через дефис)', 'slug')->required(),
                Text::make('Категория', 'category')->required(),
                Date::make('Дата события', 'starts_at')->required(),
                Textarea::make('Анонс', 'excerpt')->required(),
                Textarea::make('Описание', 'body')->required(),
                Select::make('Статус', 'status')
                    ->options(['draft' => 'Черновик', 'published' => 'Опубликовано'])
                    ->default('draft')->required(),
                Text::make('SEO-заголовок', 'seo_title'),
                Textarea::make('SEO-описание', 'seo_description'),
            ]),
        ];
    }

    protected function rules(DataWrapperContract $item): array
    {
        return [
            'slug' => ['required', 'regex:/^[a-z0-9]+(?:-[a-z0-9]+)*$/'],
            'title' => ['required', 'string', 'max:255'],
            'category' => ['required', 'string', 'max:255'],
            'starts_at' => ['required', 'date'],
            'excerpt' => ['required', 'string'],
            'body' => ['required', 'string'],
            'status' => ['required', 'in:draft,published'],
        ];
    }
}
