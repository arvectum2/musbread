<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

final class MuseumRequestTransition extends Model
{
    public $timestamps = false;
    protected $guarded = ['*'];

    public function request(): BelongsTo
    {
        return $this->belongsTo(MuseumRequest::class, 'museum_request_id');
    }
}
