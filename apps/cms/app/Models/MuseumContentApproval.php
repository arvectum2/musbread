<?php

declare(strict_types=1);

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

/** Private append-only editorial approval evidence. No update/delete UI. */
final class MuseumContentApproval extends Model
{
    protected $fillable = [
        'museum_entry_id', 'museum_event_id', 'museum_section_id', 'actor_id', 'revision_sha256', 'approved_at',
        'dispatch_status', 'publication_run_id',
    ];

    protected function casts(): array
    {
        return ['approved_at' => 'immutable_datetime'];
    }
}
