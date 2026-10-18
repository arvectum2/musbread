<?php

namespace App\Models;

use App\Support\MuseumSectionAccess;
use App\Support\MuseumVideoUrlPolicy;
use Illuminate\Auth\Access\AuthorizationException;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use Illuminate\Validation\ValidationException;

final class MuseumVideo extends Model
{
    protected $fillable=[
        'museum_entry_id','code','title','embed_url','source_url',
        'transcript','rights_confirmed','status',
    ];
    protected function casts():array { return ['rights_confirmed'=>'boolean']; }
    public function entry():BelongsTo { return $this->belongsTo(MuseumEntry::class,'museum_entry_id'); }

    protected static function booted():void
    {
        static::saving(static function(self $video):void {
            $entry=MuseumEntry::query()->find($video->museum_entry_id);
            if(!$entry)throw ValidationException::withMessages(['museum_entry_id'=>'Укажите существующий материал музея.']);
            $actor=MuseumSectionAccess::user();
            if($actor && (!MuseumSectionAccess::mayEdit($actor,$entry->museum_section_id)
                ||($video->exists&&!MuseumSectionAccess::mayEdit($actor,
                    MuseumEntry::find($video->getRawOriginal('museum_entry_id'))?->museum_section_id)))){
                throw new AuthorizationException('Нет права изменять видео чужого раздела.');
            }
            if(!preg_match('/^[a-z0-9]+(?:-[a-z0-9]+)*$/D',(string)$video->code)
                ||strlen((string)$video->code)>80){
                throw ValidationException::withMessages(['code'=>'Код: латиница, цифры и дефисы.']);
            }
            $safe=MuseumVideoUrlPolicy::safeEmbed((string)$video->embed_url);
            if($safe===null)throw ValidationException::withMessages([
                'embed_url'=>'Разрешена только безопасная HTTPS-ссылка VK/VK Видео /video_ext.php без autoplay.',
            ]);
            $video->embed_url=$safe;
            if(!MuseumVideoUrlPolicy::sourceValid((string)$video->source_url)){
                throw ValidationException::withMessages(['source_url'=>'Подтвердите HTTPS-первоисточник музея или VK.']);
            }
            if(!in_array($video->status,['draft','published'],true)){
                throw ValidationException::withMessages(['status'=>'Недопустимый статус.']);
            }
            if($video->status==='published'
                && (!$video->rights_confirmed
                    ||mb_strlen(trim((string)$video->transcript))<60
                    ||mb_strlen(trim((string)$video->title))<8)){
                throw ValidationException::withMessages([
                    'status'=>'Для публикации подтвердите права, содержательный заголовок и текстовую альтернативу не короче 60 символов.',
                ]);
            }
        });
        static::deleting(static function(self $video):void {
            $actor=MuseumSectionAccess::user();
            if($actor && !MuseumSectionAccess::mayEdit($actor,$video->entry?->museum_section_id))
                throw new AuthorizationException('Нет права удалить видео чужого раздела.');
        });
    }
}
