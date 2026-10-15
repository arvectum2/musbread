<?php

namespace App\Integrations;

/**
 * Adapter boundary in the PRIVATE contour. No routes or service credentials.
 * A real adapter may be registered only after museum approval.
 */
final readonly class MuseumIntegrationHub
{
    public function __construct(private IntegrationPort $port = new DisabledIntegrationPort()) {}

    public function execute(IntegrationRequest $intent): IntegrationResult
    {
        return $this->port->call($intent);
    }
}
