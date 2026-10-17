<?php

return [
    // Opt-in ONLY after a persistent queue worker is configured and monitored.
    // Off by default: keep the existing safe hourly direct export.
    'queue_publication' => (bool) env('MUSEUM_USE_PUBLISH_QUEUE', false),
    // Explicit private approval action and dispatch; OFF until museum-approved workflow.
    'editorial_approval_queue' => (bool) env('MUSEUM_ENABLE_APPROVAL_QUEUE', false),
    // Pre-award license-risk fallback. Default keeps the current TinyMCE CMS
    // workflow; html-source uses a built-in MoonShine textarea with NO TinyMCE
    // JS for this field. This is NOT feature parity with a WYSIWYG editor.
    'entry_body_editor' => env('MUSEUM_ENTRY_BODY_EDITOR', 'tinymce'),
    // Only local verified pre-award releases; never infer live customer deployment.
    'local_release_root' => env('MUSEUM_LOCAL_RELEASE_ROOT', base_path('../../deploy/local')),
    // Pinned project Python for optional legacy XLS normalization in non-production.
    'xls_python' => env('MUSEUM_XLS_PYTHON', 'python3'),
];
