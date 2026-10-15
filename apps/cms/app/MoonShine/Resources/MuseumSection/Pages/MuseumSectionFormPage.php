<?php

declare(strict_types=1);

namespace App\MoonShine\Resources\MuseumSection\Pages;

use App\Models\MuseumSection;
use App\MoonShine\Resources\MoonShineUser\MoonShineUserResource;
use MoonShine\Laravel\Fields\Relationships\BelongsToMany;
use MoonShine\Laravel\Models\MoonshineUser;
use Illuminate\Validation\Rule;
use MoonShine\Contracts\Core\TypeCasts\DataWrapperContract;
use MoonShine\Laravel\Pages\Crud\FormPage;
use MoonShine\UI\Components\Layout\Box;
use MoonShine\UI\Fields\ID;
use MoonShine\UI\Fields\Select;
use MoonShine\UI\Fields\Text;
use MoonShine\UI\Fields\Number;

final class MuseumSectionFormPage extends FormPage
{
    protected function fields(): iterable
    {
        $sections = MuseumSection::query()->orderBy('sort_order')->orderBy('title')->pluck('title', 'id')->all();

        return [Box::make([
            ID::make(),
            Text::make('Название раздела', 'title')->required(),
            Text::make('Slug (латиница)', 'slug')->required(),
            Select::make('Родительский раздел', 'parent_id')
                ->options($sections)->nullable(),
            Number::make('Порядок', 'sort_order')->default(0),
            Select::make('Статус', 'status')
                ->options(['draft' => 'Черновик', 'published' => 'Опубликован'])
                ->default('draft')->required(),
            Text::make('URL на действующем сайте (справочно)', 'legacy_path'),
            BelongsToMany::make(
                'Назначенные редакторы (без наследования прав)',
                'editors',
                formatted: static fn (MoonshineUser $user) => $user->name.' — '.$user->email,
                resource: MoonShineUserResource::class,
            )->selectMode(),
        ])];
    }

    protected function rules(DataWrapperContract $item): array
    {
        return [
            'title' => ['required', 'string', 'max:255'],
            'slug' => ['required', 'regex:/^[a-z0-9]+(?:-[a-z0-9]+)*$/', Rule::unique('museum_sections', 'slug')->ignore($item->getKey())],
            'parent_id' => ['nullable', 'integer', Rule::exists('museum_sections', 'id')],
            'sort_order' => ['required', 'integer', 'min:0', 'max:1000000'],
            'status' => ['required', 'in:draft,published'],
            'legacy_path' => ['nullable', 'string', 'max:250', 'regex:/^\\/(?!\\/)[a-z0-9\\/_-]*$/'],
        ];
    }
}
