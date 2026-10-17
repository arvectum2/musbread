<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Builder;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use Illuminate\Validation\ValidationException;
use Illuminate\Auth\Access\AuthorizationException;
use App\Support\MuseumSectionAccess;
use Illuminate\Database\Eloquent\Relations\BelongsToMany;

class MuseumEvent extends Model
{
    protected $fillable = [
        'slug', 'title', 'h1', 'category', 'starts_at', 'ends_at', 'excerpt', 'body',
        'status', 'published_at', 'unpublish_at', 'seo_title', 'seo_description',
        'museum_section_id', 'cover_media_id',
    ];

    protected function casts(): array
    {
        return ['starts_at' => 'date', 'ends_at' => 'date', 'published_at' => 'datetime', 'unpublish_at' => 'datetime', 'museum_section_id' => 'integer'];
    }

    protected static function booted(): void
    {
        static::deleting(static function (self $event): void {
            $actor = MuseumSectionAccess::user();
            if ($actor && ! MuseumSectionAccess::mayEdit($actor, $event->museum_section_id)) {
                throw new AuthorizationException('Удаление события другого раздела запрещено.');
            }
        });
        static::saving(function (self $event): void {
            $actor = MuseumSectionAccess::user();
            if ($actor && ! $actor->isSuperUser()) {
                $oldSection = $event->exists ? $event->getRawOriginal('museum_section_id') : null;
                if (! MuseumSectionAccess::mayEdit($actor, $event->museum_section_id)
                    || ($event->exists && ! MuseumSectionAccess::mayEdit($actor, $oldSection))) {
                    throw new AuthorizationException('Редактор не назначен на раздел события.');
                }
            }
            // A cover is selected ONLY from media attached to a currently
            // published entry in the same editorial section. Never let a
            // compromised form link a draft, foreign-section or orphan image.
            if ($event->cover_media_id !== null) {
                $media=\App\Models\MuseumMedia::query()
                    ->with('entry')->find($event->cover_media_id);
                if ($media===null || $media->entry===null
                    || $media->entry->status!=='published'
                    || $media->entry->published_at===null
                    || $media->entry->published_at->isFuture()
                    || ($media->entry->unpublish_at!==null
                        && $media->entry->unpublish_at->isPast())
                    || $media->entry->museum_section_id !== $event->museum_section_id) {
                    throw ValidationException::withMessages([
                        'cover_media_id'=>'Для афиши можно выбрать только опубликованное изображение из своего раздела.',
                    ]);
                }
            }
            if ($event->status === 'published' && $event->published_at === null) {
                $event->published_at = now();
            }
        });
    }

    public function coverMedia(): BelongsTo
    {
        return $this->belongsTo(\App\Models\MuseumMedia::class, 'cover_media_id');
    }

    public function section(): BelongsTo
    {
        return $this->belongsTo(MuseumSection::class, 'museum_section_id');
    }

    /** Existing null-section events stay administrator-owned. */
    public function scopeEditableBy(Builder $query, \MoonShine\Laravel\Models\MoonshineUser $user): Builder
    {
        if ($user->isSuperUser()) return $query;
        return $query->whereIn('museum_section_id', MuseumSectionAccess::allowedIds($user));
    }

    /** An event can be featured by multiple pages, excursions or exhibitions. */
    public function relatedEntries(): BelongsToMany
    {
        return $this->belongsToMany(MuseumEntry::class, 'museum_entry_events', 'museum_event_id', 'museum_entry_id');
    }

    public function scopePublic(Builder $query): Builder
    {
        return $query->where('status', 'published')
            ->whereNotNull('published_at')
            ->where('published_at', '<=', now())
            ->where(static fn (Builder $query) => $query
                ->whereNull('unpublish_at')->orWhere('unpublish_at', '>', now()));
    }
}
