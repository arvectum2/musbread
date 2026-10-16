<?php

declare(strict_types=1);

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

/** Every task reassignment / priority / progress edit is an append-only event. */
final class MuseumEditorialTaskUpdate extends Model
{
    public $timestamps = false;

    protected $fillable = [
        'baseline_sha256','candidate_sha256','item_group','item_key',
        'task_status','priority','assignee_id','actor_id','note',
    ];

    protected function casts(): array
    {
        return ['assignee_id'=>'integer','actor_id'=>'integer','created_at'=>'datetime'];
    }
}
