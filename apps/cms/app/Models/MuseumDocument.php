<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

final class MuseumDocument extends Model
{
    protected $fillable = [
        'museum_entry_id', 'label', 'file_type', 'storage_path',
        'sha256', 'size_bytes', 'uploaded_by',
    ];

    public function entry(): BelongsTo
    {
        return $this->belongsTo(MuseumEntry::class, 'museum_entry_id');
    }
}
