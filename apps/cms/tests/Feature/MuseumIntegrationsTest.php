<?php

namespace Tests\Feature;

use App\Integrations\DemoIntegrationPort;
use App\Integrations\DisabledIntegrationPort;
use App\Integrations\IntegrationKind;
use App\Integrations\IntegrationRequest;
use App\Integrations\MuseumIntegrationHub;
use InvalidArgumentException;
use Tests\TestCase;

class MuseumIntegrationsTest extends TestCase
{
    public function test_every_integration_is_disabled_by_default_and_no_reference_leaks(): void
    {
        $hub = new MuseumIntegrationHub();
        foreach (IntegrationKind::cases() as $kind) {
            $result = $hub->execute(new IntegrationRequest($kind));
            $this->assertSame('disabled', $result->status);
            $this->assertNull($result->reference);
            $this->assertStringNotContainsString('http', $result->message);
        }
    }

    public function test_mock_success_is_labeled_and_cannot_be_mistaken_for_real_booking(): void
    {
        $hub = new MuseumIntegrationHub(new DemoIntegrationPort());
        $result = $hub->execute(new IntegrationRequest(IntegrationKind::Ticketing, 'availability', ['resource_slug' => 'bread-history']));
        $this->assertSame('mock', $result->status);
        $this->assertSame('MOCK-tickets', $result->reference);
        $this->assertStringContainsString('не выполнена', $result->message);
    }

    public function test_demo_failure_and_timeout_return_explicit_safe_states(): void
    {
        $intent = new IntegrationRequest(IntegrationKind::ExcursionBooking);
        $failed = (new DemoIntegrationPort('failure'))->call($intent);
        $timedOut = (new DemoIntegrationPort('timeout'))->call($intent);
        $this->assertSame('error', $failed->status);
        $this->assertSame('timeout', $timedOut->status);
        $this->assertNull($failed->reference);
        $this->assertNull($timedOut->reference);
        $this->assertStringContainsString('не повторяйте', $timedOut->message);
    }

    public function test_personal_data_cannot_be_passed_in_predesign_mock_context(): void
    {
        foreach (['email', 'phone', 'visitor_name', 'message', 'token', 'api_key'] as $key) {
            try {
                new IntegrationRequest(IntegrationKind::Feedback, context: [$key => 'some-value']);
                $this->fail("Should reject {$key}");
            } catch (InvalidArgumentException $exception) {
                $this->assertStringContainsString('resource_slug', $exception->getMessage());
            }
        }
    }

    public function test_invalid_slug_and_unknown_operation_are_rejected(): void
    {
        $this->expectException(InvalidArgumentException::class);
        new IntegrationRequest(IntegrationKind::Maps, context: ['resource_slug' => '../secret']);
    }

    public function test_invalid_demo_provider_mode_is_rejected(): void
    {
        $this->expectException(InvalidArgumentException::class);
        new DemoIntegrationPort('live');
    }

    public function test_integration_hub_can_explicitly_receive_a_disabled_adapter(): void
    {
        $hub = new MuseumIntegrationHub(new DisabledIntegrationPort());
        $this->assertSame(
            'disabled',
            $hub->execute(new IntegrationRequest(IntegrationKind::Analytics))->status,
        );
    }
}
