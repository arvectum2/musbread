<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

final class MuseumDocument extends Model
{
    protected $fillable = [
        'museum_entry_id', 'label', 'file_type', 'storage_path',
        'sha256', 'size_bytes', 'uploaded_by', 'source_type',
        'accessibility_note', 'accessibility_reviewed',
        'accessible_html', 'accessible_edition_sha256',
        'accessible_reviewed_at', 'accessible_reviewed_by',
    ];

    protected function casts(): array
    {
        return [
            'accessibility_reviewed' => 'boolean',
            'accessible_reviewed_at' => 'datetime',
        ];
    }

    public function entry(): BelongsTo
    {
        return $this->belongsTo(MuseumEntry::class, 'museum_entry_id');
    }
}
