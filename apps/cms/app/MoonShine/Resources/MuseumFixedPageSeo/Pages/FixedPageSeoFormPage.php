<?php

declare(strict_types=1);

namespace App\MoonShine\Resources\MuseumFixedPageSeo\Pages;

use App\Models\MuseumFixedPageSeo;
use Illuminate\Validation\Rule;
use MoonShine\Contracts\Core\TypeCasts\DataWrapperContract;
use MoonShine\Laravel\Pages\Crud\FormPage;
use MoonShine\UI\Components\Layout\Box;
use MoonShine\UI\Fields\ID;
use MoonShine\UI\Fields\Select;
use MoonShine\UI\Fields\Text;
use MoonShine\UI\Fields\Textarea;

final class FixedPageSeoFormPage extends FormPage
{
    protected function fields(): iterable
    {
        return [Box::make([
            ID::make(),
            Text::make('Путь (например / или /news/ или /guide/museum-contacts/)', 'path')->required(),
            Text::make('SEO-заголовок страницы', 'seo_title'),
            Textarea::make('SEO-описание страницы', 'seo_description'),
            Text::make('H1 страницы', 'h1'),
            Select::make('Статус', 'status')->options([
                'draft' => 'Черновик (не экспортируется)',
                'published' => 'Утверждено для статической выгрузки',
            ])->default('draft')->required(),
        ])];
    }

    protected function rules(DataWrapperContract $item): array
    {
        return [
            'path' => ['required', 'string', 'max:255',
                static function (string $field, mixed $value, \Closure $fail): void {
                    if (! is_string($value) || ! MuseumFixedPageSeo::validFixedPath($value)) {
                        $fail('Разрешены только фиксированные маршруты сайта; у новостей/событий собственная SEO-форма.');
                    }
                },
                Rule::unique('museum_fixed_page_seo', 'path')->ignore($item->getKey())],
            'seo_title' => ['nullable', 'string', 'max:255'],
            'seo_description' => ['nullable', 'string', 'max:500'],
            'h1' => ['nullable', 'string', 'max:255'],
            'status' => ['required', 'in:draft,published'],
        ];
    }
}
