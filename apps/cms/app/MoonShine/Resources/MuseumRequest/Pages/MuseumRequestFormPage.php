<?php

declare(strict_types=1);

namespace App\MoonShine\Resources\MuseumRequest\Pages;

use App\Models\MuseumRequest;
use App\Models\MuseumSection;
use App\Support\MuseumSectionAccess;
use Illuminate\Validation\Rule;
use MoonShine\Contracts\Core\TypeCasts\DataWrapperContract;
use MoonShine\Laravel\Models\MoonshineUser;
use MoonShine\Laravel\Pages\Crud\FormPage;
use MoonShine\UI\Components\Layout\Box;
use MoonShine\UI\Fields\Date;
use MoonShine\UI\Fields\ID;
use MoonShine\UI\Fields\Number;
use MoonShine\UI\Fields\Select;
use MoonShine\UI\Fields\Text;

final class MuseumRequestFormPage extends FormPage
{
    protected function fields(): iterable
    {
        $actor = MuseumSectionAccess::user();
        if ($actor !== null && ! $actor->isSuperUser()) {
            return [Box::make([
                ID::make(),
                Select::make('Статус обработки', 'status')
                    ->options(MuseumRequest::STATUSES)->required(),
            ])];
        }

        return [Box::make([
            ID::make(),
            Text::make('Номер обращения (автоматический)', 'reference')->readonly(),
            Select::make('Тип', 'type')->options(MuseumRequest::TYPES)->required(),
            Select::make('Тема (без персональных данных)', 'topic')
                ->options(MuseumRequest::TOPICS)->required(),
            Select::make('Статус', 'status')->options(MuseumRequest::STATUSES)
                ->default('new')->required(),
            Select::make('Раздел сайта', 'museum_section_id')
                ->options(MuseumSection::query()->orderBy('title')->pluck('title', 'id')->all())
                ->nullable(),
            Select::make('Назначить редактору', 'assigned_to_id')
                ->options(MoonshineUser::query()->orderBy('name')->pluck('name', 'id')->all())
                ->nullable(),
            Date::make('Желаемая дата экскурсии (только демо)', 'preferred_date')->nullable(),
            Number::make('Размер группы (1–100)', 'group_size')->nullable(),
        ])];
    }

    protected function rules(DataWrapperContract $item): array
    {
        if (MuseumSectionAccess::user() !== null && ! MuseumSectionAccess::user()->isSuperUser()) {
            return ['status' => ['required', Rule::in(array_keys(MuseumRequest::STATUSES))]];
        }

        return [
            'type' => ['required', Rule::in(array_keys(MuseumRequest::TYPES))],
            'topic' => ['required', Rule::in(array_keys(MuseumRequest::TOPICS))],
            'status' => ['required', Rule::in(array_keys(MuseumRequest::STATUSES))],
            'museum_section_id' => ['nullable', 'integer', Rule::exists('museum_sections', 'id')],
            'assigned_to_id' => ['nullable', 'integer', Rule::exists('moonshine_users', 'id')],
            'preferred_date' => ['nullable', 'date'],
            'group_size' => ['nullable', 'integer', 'min:1', 'max:100'],
        ];
    }
}
