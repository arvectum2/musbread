<?php

namespace App\Integrations;

interface IntegrationPort
{
    public function call(IntegrationRequest $request): IntegrationResult;
}
