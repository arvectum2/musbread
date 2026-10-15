<?php

namespace App\Integrations;

/** Production-safe default: no HTTP, no billing, no false booking receipts. */
final class DisabledIntegrationPort implements IntegrationPort
{
    public function call(IntegrationRequest $request): IntegrationResult
    {
        return IntegrationResult::disabled();
    }
}
