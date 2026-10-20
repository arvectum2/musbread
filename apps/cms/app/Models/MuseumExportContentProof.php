<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

/** Private immutable observation of the record bytes inside one exported snapshot. */
final class MuseumExportContentProof extends Model
{
    public $timestamps = false;

    protected $fillable = [
        'publication_run_id','approval_id','subject_kind','subject_id',
        'revision_sha256','snapshot_sha256','export_record_sha256',
    ];
}
