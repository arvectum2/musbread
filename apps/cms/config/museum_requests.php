<?php
return [
    // Disabled by default, including production. No real PII without museum sign-off.
    'enabled' => (bool) env('MUSEUM_REQUEST_IMPORT_ENABLED', false),
    'url' => env('MUSEUM_REQUEST_INGRESS_PRIVATE_URL', ''),
    'token' => env('MUSEUM_REQUEST_INGRESS_TOKEN', ''),
    'secret_key' => env('MUSEUM_REQUEST_SEAL_SECRET_KEY', ''),
    'tls_cert' => env('MUSEUM_REQUEST_TLS_CLIENT_CERT', ''),
    'tls_key' => env('MUSEUM_REQUEST_TLS_CLIENT_KEY', ''),
    'tls_ca' => env('MUSEUM_REQUEST_TLS_CA', ''),
    'consent_version' => env('MUSEUM_REQUEST_CONSENT_VERSION', ''),
];
