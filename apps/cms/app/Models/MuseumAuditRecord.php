<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class MuseumAuditRecord extends Model
{
    public $timestamps = false;

    protected $fillable = ['subject_type', 'subject_id', 'action', 'actor_id', 'changed_fields'];

    protected function casts(): array
    {
        return [
            'changed_fields' => 'array',
            'created_at' => 'datetime',
        ];
    }
}
