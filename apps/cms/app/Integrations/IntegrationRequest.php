<?php

namespace App\Integrations;

use InvalidArgumentException;

/**
 * Safe pre-award intent. Real visitor records are deliberately out of scope:
 * no form submissions, payment credentials, email, telephone or IP allowed.
 */
final readonly class IntegrationRequest
{
    public function __construct(
        public IntegrationKind $kind,
        public string $operation = 'availability',
        public array $context = [],
    ) {
        if (! preg_match('/^[a-z][a-z0-9_-]{0,35}$/', $operation)) {
            throw new InvalidArgumentException('Invalid operation name');
        }

        // Context is only a non-identifying slug, no arbitrary visitor payload.
        $allowed = ['resource_slug'];
        foreach ($context as $key => $value) {
            if (! in_array($key, $allowed, true)
                || ! is_string($value)
                || ! preg_match('/^[a-z0-9][a-z0-9-]{0,95}$/', $value)) {
                throw new InvalidArgumentException('Only a non-identifying resource_slug is allowed before customer API approval');
            }
        }
    }
}
