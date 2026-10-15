<?php

namespace Tests\Feature;

use Illuminate\Foundation\Testing\RefreshDatabase;
use Tests\TestCase;

class MoonShineAccessTest extends TestCase
{
    use RefreshDatabase;

    public function test_admin_requires_authentication(): void
    {
        $response = $this->get('/admin');
        $response->assertRedirect('/admin/login');
    }

    public function test_login_form_is_accessible(): void
    {
        $this->get('/admin/login')->assertOk();
    }
}
