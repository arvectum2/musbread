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
use Illuminate\Validation\Rule;

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
                Date::make('Дата начала', 'starts_at')->required(),
                Date::make('Дата окончания (если событие многодневное)', 'ends_at')->nullable(),
                Textarea::make('Анонс', 'excerpt')->required(),
                Textarea::make('Описание', 'body')->required(),
                Select::make('Статус', 'status')
                    ->options(['draft' => 'Черновик', 'published' => 'Опубликовано'])
                    ->default('draft')->required(),
                Date::make('Публиковать с (дата и время)', 'published_at')->withTime()->nullable(),
                Text::make('SEO-заголовок', 'seo_title'),
                Textarea::make('SEO-описание', 'seo_description'),
            ]),
        ];
    }

    protected function rules(DataWrapperContract $item): array
    {
        return [
            'slug' => ['required', 'regex:/^[a-z0-9]+(?:-[a-z0-9]+)*$/', Rule::unique('museum_events', 'slug')->ignore($item->getKey())],
            'title' => ['required', 'string', 'max:255'],
            'category' => ['required', 'string', 'max:255'],
            'starts_at' => ['required', 'date'],
            'ends_at' => ['nullable', 'date', 'after_or_equal:starts_at'],
            'excerpt' => ['required', 'string'],
            'body' => ['required', 'string'],
            'status' => ['required', 'in:draft,published'],
            'published_at' => ['nullable', 'date'],
        ];
    }
}
