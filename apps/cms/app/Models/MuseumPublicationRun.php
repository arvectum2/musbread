<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class MuseumPublicationRun extends Model
{
    protected $fillable = [
        'status', 'attempts', 'snapshot_sha256', 'error_type', 'started_at', 'finished_at',
        'content_verified_at', 'content_proof_count', 'manifest_sha256',
    ];

    protected function casts(): array
    {
        return ['started_at' => 'datetime', 'finished_at' => 'datetime',
            'content_verified_at' => 'datetime', 'content_proof_count' => 'integer'];
    }
}
