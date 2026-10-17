<?php

namespace App\Models;

use DomainException;
use Illuminate\Database\Eloquent\Builder;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use Illuminate\Database\Eloquent\Relations\BelongsToMany;
use Illuminate\Database\Eloquent\Relations\HasMany;
use Illuminate\Validation\ValidationException;

/** Editable, hierarchical navigation. Only approved branches leave the private CMS. */
class MuseumSection extends Model
{
    protected $fillable = ['parent_id', 'slug', 'title', 'sort_order', 'status', 'legacy_path'];

    protected function casts(): array
    {
        return ['sort_order' => 'integer'];
    }

    public function parent(): BelongsTo
    {
        return $this->belongsTo(self::class, 'parent_id');
    }

    public function children(): HasMany
    {
        return $this->hasMany(self::class, 'parent_id');
    }

    public function entries(): HasMany
    {
        return $this->hasMany(MuseumEntry::class, 'museum_section_id');
    }

    public function events(): HasMany
    {
        return $this->hasMany(MuseumEvent::class, 'museum_section_id');
    }

    public function requests(): HasMany
    {
        return $this->hasMany(MuseumRequest::class, 'museum_section_id');
    }

    public function editors(): BelongsToMany
    {
        return $this->belongsToMany(
            \MoonShine\Laravel\Models\MoonshineUser::class,
            'museum_section_editor',
            'museum_section_id',
            'moonshine_user_id'
        );
    }

    public function scopePublic(Builder $builder): Builder
    {
        return $builder->where('status', 'published');
    }

    protected static function booted(): void
    {
        static::saving(static function (self $section): void {
            if ($section->status !== 'draft' && $section->status !== 'published') {
                throw ValidationException::withMessages(['status' => 'Недопустимый статус раздела']);
            }
            if (! preg_match('/^[a-z0-9]+(?:-[a-z0-9]+)*$/D', $section->slug)) {
                throw ValidationException::withMessages(['slug' => 'Адрес раздела должен содержать только латиницу, цифры и дефис']);
            }
            if ($section->legacy_path !== null
                && ! preg_match('#^/(?!/)[a-z0-9/_-]*$#D', $section->legacy_path)) {
                throw ValidationException::withMessages([
                    'legacy_path' => 'Допустима только относительная ссылка на действующий музейный сайт.',
                ]);
            }
            $seen = $section->exists ? [$section->getKey() => true] : [];
            $parent = $section->parent_id;
            while ($parent !== null) {
                if (isset($seen[$parent])) {
                    throw ValidationException::withMessages(['parent_id' => 'Раздел нельзя вложить в самого себя или своего потомка']);
                }
                $seen[$parent] = true;
                $parent = self::query()->whereKey($parent)->value('parent_id');
                if (count($seen) > 500) {
                    throw new DomainException('Unreasonable navigation depth');
                }
            }
        });
        static::deleting(static function (self $section): void {
            if ($section->children()->exists() || $section->entries()->exists()
                || $section->events()->exists()
                || $section->requests()->exists()) {
                throw ValidationException::withMessages([
                    'section' => 'Нельзя удалить раздел с дочерними страницами, материалами, событиями или обращениями.',
                ]);
            }
        });
    }
}
