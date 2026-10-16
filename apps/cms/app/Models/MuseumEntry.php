<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Builder;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use App\Support\MuseumSectionAccess;
use Illuminate\Auth\Access\AuthorizationException;
use Illuminate\Database\Eloquent\Model;
use App\Support\MuseumHtmlSanitizer;
use Illuminate\Database\Eloquent\Relations\HasMany;
use Illuminate\Database\Eloquent\Relations\BelongsToMany;

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
        'type', 'slug', 'title', 'h1', 'parent_slug', 'museum_section_id', 'excerpt', 'body',
        'status', 'published_at', 'seo_title', 'seo_description', 'sort_order',
        'title_en', 'excerpt_en', 'body_en', 'seo_title_en', 'seo_description_en',
    ];

    protected function casts(): array
    {
        return [
            'published_at' => 'datetime',
            'sort_order' => 'integer',
            'museum_section_id' => 'integer',
        ];
    }

    protected static function booted(): void
    {
        static::deleting(static function (self $entry): void {
            if ($entry->documents()->exists()) {
                throw \Illuminate\Validation\ValidationException::withMessages([
                    'documents' => 'Сначала отвяжите или удалите файлы документов.',
                ]);
            }
            $actor = MuseumSectionAccess::user();
            if ($actor && ! MuseumSectionAccess::mayEdit($actor, $entry->museum_section_id)) {
                throw new AuthorizationException('Удаление материала другого раздела запрещено.');
            }
        });
        static::saving(static function (self $entry): void {
            $actor = MuseumSectionAccess::user();
            if ($actor && ! $actor->isSuperUser()) {
                $oldSection = $entry->exists ? $entry->getRawOriginal('museum_section_id') : null;
                if (! MuseumSectionAccess::mayEdit($actor, $entry->museum_section_id)
                    || ($entry->exists && ! MuseumSectionAccess::mayEdit($actor, $oldSection))) {
                    throw new AuthorizationException('Редактор не назначен на этот раздел.');
                }
            }
            if ($entry->isDirty('body') && $entry->body !== null) {
                $entry->body = app(MuseumHtmlSanitizer::class)->clean((string) $entry->body);
            }
            if ($entry->isDirty('body_en') && $entry->body_en !== null) {
                $entry->body_en = app(MuseumHtmlSanitizer::class)->clean((string) $entry->body_en);
            }

            if ($entry->status === 'published' && $entry->published_at === null) {
                $entry->published_at = now();
            }
        });
    }

    public function section(): BelongsTo
    {
        return $this->belongsTo(MuseumSection::class, 'museum_section_id');
    }

    public function documents(): HasMany
    {
        return $this->hasMany(MuseumDocument::class, 'museum_entry_id');
    }

    public function media(): HasMany
    {
        return $this->hasMany(MuseumMedia::class, 'museum_entry_id');
    }

    /** Editorially curated, directed related-content links. */
    public function relatedEntries(): BelongsToMany
    {
        return $this->belongsToMany(self::class, 'museum_entry_relations', 'source_entry_id', 'target_entry_id');
    }

    public function linkedEvents(): BelongsToMany
    {
        return $this->belongsToMany(MuseumEvent::class, 'museum_entry_events', 'museum_entry_id', 'museum_event_id');
    }

    public function scopeEditableBy(Builder $query, \MoonShine\Laravel\Models\MoonshineUser $user): Builder
    {
        if ($user->isSuperUser()) return $query;
        return $query->whereIn('museum_section_id', MuseumSectionAccess::allowedIds($user));
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
