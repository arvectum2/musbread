<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Builder;
use Illuminate\Database\Eloquent\Relations\BelongsToMany;

class MuseumEvent extends Model
{
    protected $fillable = [
        'slug', 'title', 'category', 'starts_at', 'excerpt', 'body',
        'status', 'published_at', 'seo_title', 'seo_description',
    ];

    protected function casts(): array
    {
        return ['starts_at' => 'date', 'published_at' => 'datetime'];
    }

    protected static function booted(): void
    {
        static::saving(function (self $event): void {
            if ($event->status === 'published' && $event->published_at === null) {
                $event->published_at = now();
            }
        });
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
            ->where('published_at', '<=', now());
    }
}
