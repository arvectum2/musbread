<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Builder;
use Illuminate\Database\Eloquent\Model;
use App\Support\MuseumHtmlSanitizer;
use Illuminate\Database\Eloquent\Relations\HasMany;

class MuseumEntry extends Model
{
    public const TYPES = [
        'page' => 'Информационная страница',
        'news' => 'Новость',
        'excursion' => 'Экскурсия',
        'exhibition' => 'Выставка',
        'document' => 'Документ',
    ];

    protected $fillable = [
        'type', 'slug', 'title', 'h1', 'parent_slug', 'excerpt', 'body',
        'status', 'published_at', 'seo_title', 'seo_description', 'sort_order',
    ];

    protected function casts(): array
    {
        return [
            'published_at' => 'datetime',
            'sort_order' => 'integer',
        ];
    }

    protected static function booted(): void
    {
        static::saving(static function (self $entry): void {
            if ($entry->isDirty('body') && $entry->body !== null) {
                $entry->body = app(MuseumHtmlSanitizer::class)->clean((string) $entry->body);
            }

            if ($entry->status === 'published' && $entry->published_at === null) {
                $entry->published_at = now();
            }
        });
    }

    public function media(): HasMany
    {
        return $this->hasMany(MuseumMedia::class, 'museum_entry_id');
    }

    public function scopePublic(Builder $query): Builder
    {
        return $query->where('status', 'published')
            ->whereNotNull('published_at')
            ->where('published_at', '<=', now());
    }

    public function scopeOfType(Builder $query, string $type): Builder
    {
        return $query->where('type', $type);
    }
}
