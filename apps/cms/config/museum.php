<?php

return [
    // Opt-in ONLY after a persistent queue worker is configured and monitored.
    // Off by default: keep the existing safe hourly direct export.
    'queue_publication' => (bool) env('MUSEUM_USE_PUBLISH_QUEUE', false),
];
