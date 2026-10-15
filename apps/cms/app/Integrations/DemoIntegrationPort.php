<?php

namespace App\Integrations;

use InvalidArgumentException;

/**
 * Deterministic offline fake. Use only in tests/demos, never with real visitor
 * data or production feature flags. No side effects and no network transport.
 */
final readonly class DemoIntegrationPort implements IntegrationPort
{
    public function __construct(private string $behavior = 'success')
    {
        if (! in_array($behavior, ['success', 'failure', 'timeout'], true)) {
            throw new InvalidArgumentException('Unsupported demo behavior');
        }
    }

    public function call(IntegrationRequest $request): IntegrationResult
    {
        return match ($this->behavior) {
            'success' => IntegrationResult::mock($request->kind),
            'failure' => IntegrationResult::failure(),
            'timeout' => IntegrationResult::timeout(),
        };
    }
}
