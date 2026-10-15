<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class MuseumPublicationRun extends Model
{
    protected $fillable = [
        'status', 'attempts', 'snapshot_sha256', 'error_type', 'started_at', 'finished_at',
    ];

    protected function casts(): array
    {
        return ['started_at' => 'datetime', 'finished_at' => 'datetime'];
    }
}
