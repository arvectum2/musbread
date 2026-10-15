<?php

namespace Tests\Feature;

use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\RateLimiter;
use MoonShine\Laravel\Models\MoonshineUser;
use Tests\TestCase;

class MuseumRateLimitTest extends TestCase
{
    use RefreshDatabase;

    private function clear(string $scope): void
    {
        RateLimiter::clear('musbread:rate:'.$scope.':'.hash('sha256', '127.0.0.1'));
    }

    public function test_login_is_limited_by_client_ip_not_username(): void
    {
        $this->clear('login');
        try {
            for ($i = 0; $i < 8; $i++) {
                $this->post('/admin/authenticate', [
                    'username' => "no-such-user{$i}@example.invalid",
                    'password' => 'guess-'.$i,
                ])->assertStatus(302);
            }
            $this->post('/admin/authenticate', [
                'username' => 'one-more@example.invalid',
                'password' => 'guess',
            ])->assertStatus(429)->assertHeader('Retry-After');
        } finally {
            $this->clear('login');
        }
    }

    public function test_upload_budget_blocks_excess_and_does_not_affect_get(): void
    {
        $this->clear('upload');
        $this->actingAs(MoonshineUser::factory()->create(), 'moonshine');
        try {
            // Valid file is not required: rejected form submissions still consume
            // the upload attempt budget before reaching the controller.
            for ($i = 0; $i < 30; $i++) {
                $this->post('/admin/museum-media', [])->assertStatus(302);
            }
            $this->post('/admin/museum-media', [])->assertStatus(429);
            $this->get('/admin/museum-media')->assertOk();
        } finally {
            $this->clear('upload');
        }
    }

    public function test_non_sensitive_routes_are_not_throttled_by_login_budget(): void
    {
        $this->clear('login');
        $this->actingAs(MoonshineUser::factory()->create(), 'moonshine')
            ->get('/admin')->assertOk();
    }
}
