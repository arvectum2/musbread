<?php
declare(strict_types=1);
namespace App\MoonShine\Resources\MuseumVisitorContacts\Pages;
use App\Models\MuseumVisitorContacts;
use Illuminate\Validation\Rule;
use MoonShine\Contracts\Core\TypeCasts\DataWrapperContract;
use MoonShine\Laravel\Pages\Crud\FormPage;
use MoonShine\UI\Components\Layout\Box;
use MoonShine\UI\Fields\ID;
use MoonShine\UI\Fields\Select;
use MoonShine\UI\Fields\Text;
final class VisitorContactsFormPage extends FormPage {
    protected function fields():iterable {
        return [Box::make([
            ID::make(),
            Text::make('Карточка сведений (primary)','scope')->default('primary')->required(),
            Text::make('Официальный адрес','address'),
            Text::make('Ближайшее метро','metro'),
            Text::make('Номер для посетителей','phone'),
            Text::make('Ссылка для звонка tel:+…','phone_href'),
            Text::make('Электронная почта','email'),
            Text::make('Режим работы','opening_hours'),
            Text::make('Время окончания входа','admission_hours'),
            Text::make('Выходной день','closed_day'),
            Text::make('Санитарный день','sanitary_day'),
            Select::make('Статус','status')->options([
                'draft'=>'Черновик (не выгружается)',
                'published'=>'Утверждено к выгрузке',
            ])->default('draft')->required(),
        ])];
    }
    protected function rules(DataWrapperContract $item):array {
        $rules=[
            'scope'=>['required','in:primary',Rule::unique('museum_visitor_contacts','scope')->ignore($item->getKey())],
            'status'=>['required','in:draft,published'],
            'email'=>['nullable','email','max:255'],
            'phone_href'=>['nullable','regex:/^tel:\+[0-9]{8,15}$/','max:255'],
        ];
        foreach(MuseumVisitorContacts::FACTS as $field)
            if(!array_key_exists($field,$rules)) $rules[$field]=['nullable','string','max:255'];
        return $rules;
    }
}
