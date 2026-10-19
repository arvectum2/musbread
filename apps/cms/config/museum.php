<?php

return [
    // Opt-in ONLY after a persistent queue worker is configured and monitored.
    // Off by default: keep the existing safe hourly direct export.
    'queue_publication' => (bool) env('MUSEUM_USE_PUBLISH_QUEUE', false),
    // Optional isolated worker export destination, never a public webroot.
    // Intended for pre-award QA and later customer-approved private staging.
    'queued_export_staging_dir' => env('MUSEUM_QUEUED_EXPORT_STAGING_DIR'),
    // Explicit private approval action and dispatch; OFF until museum-approved workflow.
    'editorial_approval_queue' => (bool) env('MUSEUM_ENABLE_APPROVAL_QUEUE', false),
    // MIT-licensed self-hosted Jodit is default. html-source remains safe fallback.
    'entry_body_editor' => env('MUSEUM_ENTRY_BODY_EDITOR', 'jodit'),
    // Only local verified pre-award releases; never infer live customer deployment.
    'local_release_root' => env('MUSEUM_LOCAL_RELEASE_ROOT', base_path('../../deploy/local')),
    // Pinned project Python for optional legacy XLS normalization in non-production.
    'xls_python' => env('MUSEUM_XLS_PYTHON', 'python3'),
];
