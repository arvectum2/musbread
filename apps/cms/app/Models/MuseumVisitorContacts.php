<?php
namespace App\Models;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Validation\ValidationException;

/** Museum-owned, approved visitor facts; reference text remains a fallback
 * until the first complete, separately reviewed contact card is published. */
final class MuseumVisitorContacts extends Model
{
    protected $table = 'museum_visitor_contacts';
    protected $fillable = ['scope','status','address','metro','phone','phone_href','email',
        'opening_hours','admission_hours','closed_day','sanitary_day'];
    public const FACTS = ['address','metro','phone','phone_href','email','opening_hours',
        'admission_hours','closed_day','sanitary_day'];
    protected static function booted(): void {
        static::saving(static function(self $record): void {
            if ($record->scope !== 'primary') throw ValidationException::withMessages([
                'scope'=>'Предусмотрена только одна официальная карточка сведений о посещении.']);
            if (!in_array($record->status,['draft','published'],true))
                throw ValidationException::withMessages(['status'=>'Недопустимый статус карточки.']);
            // Publishing a partial card would silently mix inconsistent
            // contact details from different dates/sources. Fail closed.
            if ($record->status === 'published') {
                foreach(self::FACTS as $field) {
                    if(trim((string)$record->$field) === '')
                        throw ValidationException::withMessages([$field=>'Для публикации заполните все официальные сведения.']);
                }
            }
            if ($record->phone_href !== null
                && !preg_match('/^tel:\+[0-9]{8,15}$/D',(string)$record->phone_href)) {
                throw ValidationException::withMessages(['phone_href'=>'Телефонная ссылка: tel:+ и от 8 до 15 цифр.']);
            }
            if ($record->email !== null && !filter_var($record->email,FILTER_VALIDATE_EMAIL)) {
                throw ValidationException::withMessages(['email'=>'Нужен действительный адрес электронной почты.']);
            }
            foreach (self::FACTS as $field) {
                if (mb_strlen((string)$record->$field)>255) throw ValidationException::withMessages([
                    $field=>'Не более 255 символов.']);
            }
        });
    }
}
