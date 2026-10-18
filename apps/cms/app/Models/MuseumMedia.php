<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class MuseumMedia extends Model
{
    protected $table = 'museum_media';

    protected $fillable = [
        'museum_entry_id', 'storage_path', 'sha256', 'alt', 'caption', 'long_description',
        'mime', 'width', 'height', 'size_bytes', 'uploaded_by',
        'source_rights_pending', 'source_original_url', 'source_original_sha256',
    ];

    protected function casts(): array
    {
        return ['source_rights_pending' => 'boolean'];
    }

    public function entry(): BelongsTo
    {
        return $this->belongsTo(MuseumEntry::class, 'museum_entry_id');
    }
}
