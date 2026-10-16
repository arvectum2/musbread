<?php

declare(strict_types=1);

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

/** Append-only internal editor notes, never legal approval. */
final class MuseumEditorialReviewNote extends Model
{
    public $timestamps = false;

    protected $fillable = [
        'baseline_sha256', 'candidate_sha256', 'item_group',
        'item_key', 'decision', 'note', 'actor_id',
    ];

    protected function casts(): array
    {
        return ['created_at' => 'datetime'];
    }
}
