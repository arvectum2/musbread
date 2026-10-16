<?php

return [
    // Opt-in ONLY after a persistent queue worker is configured and monitored.
    // Off by default: keep the existing safe hourly direct export.
    'queue_publication' => (bool) env('MUSEUM_USE_PUBLISH_QUEUE', false),
    // Pre-award license-risk fallback. Default keeps the current TinyMCE CMS
    // workflow; html-source uses a built-in MoonShine textarea with NO TinyMCE
    // JS for this field. This is NOT feature parity with a WYSIWYG editor.
    'entry_body_editor' => env('MUSEUM_ENTRY_BODY_EDITOR', 'tinymce'),
    // Only local verified pre-award releases; never infer live customer deployment.
    'local_release_root' => env('MUSEUM_LOCAL_RELEASE_ROOT', base_path('../../deploy/local')),
];
