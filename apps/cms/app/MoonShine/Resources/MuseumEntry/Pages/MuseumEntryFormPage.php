<?php

declare(strict_types=1);

namespace App\MoonShine\Resources\MuseumEntry\Pages;

use App\Models\MuseumEntry;
use App\Models\MuseumSection;
use App\Support\MuseumSectionAccess;
use Illuminate\Validation\Rule;
use MoonShine\Contracts\Core\TypeCasts\DataWrapperContract;
use MoonShine\Laravel\Pages\Crud\FormPage;
use MoonShine\UI\Components\Layout\Box;
use MoonShine\UI\Fields\Date;
use MoonShine\UI\Fields\ID;
use MoonShine\UI\Fields\Select;
use MoonShine\UI\Fields\Text;
use MoonShine\UI\Fields\Textarea;
use MoonShine\TinyMce\Fields\TinyMce;

final class MuseumEntryFormPage extends FormPage
{
    protected function fields(): iterable
    {
        return [
            Box::make([
                ID::make(),
                Select::make('Раздел', 'type')
                    ->options(MuseumEntry::TYPES)->required(),
                Text::make('Название', 'title')->required(),
                Text::make('URL (латиница, через дефис)', 'slug')->required(),
                Text::make('H1', 'h1'),
                Select::make('Раздел сайта', 'museum_section_id')
                    ->options(MuseumSection::query()
                        ->whereIn('id', MuseumSectionAccess::user()
                            ? MuseumSectionAccess::allowedIds(MuseumSectionAccess::user()) : [])
                        ->orderBy('sort_order')->pluck('title', 'id')->all())
                    ->nullable(),
                Textarea::make('Анонс', 'excerpt'),
                TinyMce::make('Основной текст', 'body')
                    ->locale('ru')
                    ->plugins(['autolink', 'link', 'lists', 'wordcount', 'autoresize'])
                    ->menubar(false)
                    ->toolbar('undo redo | blocks | bold italic | bullist numlist | link | removeformat')
                    ->addOption('license_key', 'gpl')
                    ->required(),
                Select::make('Статус', 'status')
                    ->options(['draft' => 'Черновик', 'published' => 'Опубликовано'])
                    ->default('draft')->required(),
                Date::make('Публиковать с (дата и время)', 'published_at')->withTime()->nullable(),
                Text::make('SEO-заголовок', 'seo_title'),
                Textarea::make('SEO-описание', 'seo_description'),
                Text::make('English title (publish only with English body)', 'title_en'),
                Textarea::make('English excerpt', 'excerpt_en'),
                Textarea::make('English body (safe HTML)', 'body_en'),
                Text::make('English SEO title', 'seo_title_en'),
                Textarea::make('English SEO description', 'seo_description_en'),
            ]),
        ];
    }

    protected function rules(DataWrapperContract $item): array
    {
        return [
            'type' => ['required', Rule::in(array_keys(MuseumEntry::TYPES))],
            'slug' => ['required', 'regex:/^[a-z0-9]+(?:-[a-z0-9]+)*$/', Rule::unique('museum_entries', 'slug')->ignore($item->getKey())],
            'title' => ['required', 'string', 'max:255'],
            'body' => ['required', 'string'],
            'museum_section_id' => ['nullable', 'integer', Rule::exists('museum_sections', 'id')],
            'status' => ['required', 'in:draft,published'],
            'published_at' => ['nullable', 'date'],
            'title_en' => ['nullable', 'string', 'max:255'],
            'excerpt_en' => ['nullable', 'string'],
            'body_en' => ['nullable', 'string'],
            'seo_title_en' => ['nullable', 'string', 'max:255'],
            'seo_description_en' => ['nullable', 'string'],
        ];
    }
}
