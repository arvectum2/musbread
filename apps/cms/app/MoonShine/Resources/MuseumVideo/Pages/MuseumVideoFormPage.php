<?php
declare(strict_types=1);
namespace App\MoonShine\Resources\MuseumVideo\Pages;

use App\Models\MuseumEntry;
use App\Support\MuseumSectionAccess;
use Illuminate\Validation\Rule;
use MoonShine\Contracts\Core\TypeCasts\DataWrapperContract;
use MoonShine\Laravel\Pages\Crud\FormPage;
use MoonShine\UI\Components\Layout\Box;
use MoonShine\UI\Fields\ID;
use MoonShine\UI\Fields\Text;
use MoonShine\UI\Fields\Select;
use MoonShine\UI\Fields\Textarea;
use MoonShine\UI\Fields\Checkbox;

final class MuseumVideoFormPage extends FormPage {
    protected function fields():iterable {
        $user=MuseumSectionAccess::user();
        return [Box::make([
            ID::make(),
            Select::make('Материал-владелец (с правом редактирования)','museum_entry_id')
                ->options($user?MuseumEntry::editableBy($user)->orderBy('title')
                    ->pluck('title','id')->all():[])->required(),
            Text::make('Код видео — латиница и дефисы','code')->required(),
            Text::make('Название видеозаписи','title')->required(),
            Text::make('VK-вставка https://vk.com/video_ext.php?oid=…&id=…','embed_url')->required(),
            Text::make('Официальная страница-источник','source_url')->required(),
            Textarea::make('Текстовая альтернатива видео (минимум 60 символов)','transcript')->required(),
            Checkbox::make('Подтверждены права на встраивание','rights_confirmed'),
            Select::make('Статус','status')->options([
                'draft'=>'Черновик — не публиковать',
                'published'=>'Проверено и одобрено',
            ])->default('draft')->required(),
        ])];
    }
    protected function rules(DataWrapperContract $item):array {
        return [
            'museum_entry_id'=>['required','integer',Rule::exists('museum_entries','id')],
            'code'=>['required','regex:/^[a-z0-9]+(?:-[a-z0-9]+)*$/','max:80',
                Rule::unique('museum_videos','code')->where(
                    fn($q)=>$q->where('museum_entry_id',request('museum_entry_id')))
                    ->ignore($item->getKey())],
            'title'=>['required','string','min:8','max:255'],
            'embed_url'=>['required','string','max:700'],
            'source_url'=>['required','url','max:700'],
            // The editor can save an incomplete video privately. The
            // publication transition is blocked by BOTH rules and Model.
            'transcript'=>['nullable','string','max:50000',
                Rule::requiredIf(request('status')==='published'),
                Rule::when(request('status')==='published',['min:60'])],
            'rights_confirmed'=>['boolean'],
            'status'=>['required','in:draft,published'],
        ];
    }
}
