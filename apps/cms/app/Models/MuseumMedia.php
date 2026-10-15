<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class MuseumMedia extends Model
{
    protected $table = 'museum_media';

    protected $fillable = [
        'museum_entry_id', 'storage_path', 'sha256', 'alt', 'caption',
        'mime', 'width', 'height', 'size_bytes', 'uploaded_by',
    ];

    public function entry(): BelongsTo
    {
        return $this->belongsTo(MuseumEntry::class, 'museum_entry_id');
    }
}
