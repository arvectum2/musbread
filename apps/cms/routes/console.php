<?php

use Illuminate\Foundation\Inspiring;
use Illuminate\Support\Facades\Artisan;
use Illuminate\Support\Facades\Schedule;

Artisan::command('inspire', function () {
    $this->comment(Inspiring::quote());
})->purpose('Display an inspiring quote');


// Prepare a read-only content export every hour. The actual transport to the
// customer's isolated public server must be configured after network approval.
if (config('museum.queue_publication', false)) {
    Schedule::command('museum:queue-export')->hourly()->withoutOverlapping();
    Schedule::command('museum:recover-stale-publications')->everyTenMinutes()->withoutOverlapping();
} else {
    // The direct hourly mode is the DEFAULT in the pre-contract stage.
    // It must be at least as strict as the queued worker: never publish
    // material with a critical link/editorial error unattended.
    Schedule::command('museum:export --preflight-strict')->hourly()->withoutOverlapping();
}
