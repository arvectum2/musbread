<?php

namespace Tests\Feature;

use App\Models\MuseumEvent;
use App\Models\MuseumSection;
use Illuminate\Foundation\Testing\RefreshDatabase;
use MoonShine\Laravel\Models\MoonshineUser;
use MoonShine\Laravel\Models\MoonshineUserRole;
use Tests\TestCase;

class MuseumRoleAccessTest extends TestCase
{
    use RefreshDatabase;

    private function editor(): MoonshineUser
    {
        $role = MoonshineUserRole::query()->firstOrCreate(['name' => 'Editor']);
        return MoonshineUser::factory()->create(['moonshine_user_role_id' => $role->id]);
    }

    public function test_editor_can_create_a_museum_draft(): void
    {
        $section = MuseumSection::create([
            'slug'=>'event-news', 'title'=>'Новости музея', 'status'=>'published',
        ]);
        $editor = $this->editor();
        $section->editors()->attach($editor->id);
        $this->actingAs($editor, 'moonshine')
            ->post('/admin/resource/museum-event-resource/crud', [
                'museum_section_id' => $section->id,
                'slug' => 'editor-event',
                'title' => 'Редакторский черновик',
                'category' => 'Новость',
                'starts_at' => '2026-11-10',
                'excerpt' => 'Описание',
                'body' => 'Подробное описание',
                'status' => 'draft',
            ])->assertStatus(302);

        $this->assertDatabaseHas('museum_events', ['slug' => 'editor-event', 'status' => 'draft']);
    }

    public function test_editor_cannot_create_administrators_or_roles(): void
    {
        $editor = $this->editor();
        $this->assertFalse($editor->isSuperUser());
        $this->actingAs($editor, 'moonshine');

        $this->post('/admin/resource/moon-shine-user-resource/crud', [
            'name' => 'Unauthorised admin', 'email' => 'fake@example.invalid',
        ])->assertForbidden();

        $this->post('/admin/resource/moon-shine-user-role-resource/crud', [
            'name' => 'Admin',
        ])->assertForbidden();

        $this->assertSame(1, MoonshineUser::count());
        $this->assertSame(2, MoonshineUserRole::count());
    }

    public function test_editor_cannot_read_administrator_list(): void
    {
        $this->actingAs($this->editor(), 'moonshine')
            ->getJson('/admin/resource/moon-shine-user-resource/crud')
            ->assertForbidden();
    }

    public function test_editor_cannot_open_administrator_or_role_pages(): void
    {
        $this->actingAs($this->editor(), 'moonshine')
            ->get('/admin/resource/moon-shine-user-resource/moon-shine-user-index-page')
            ->assertForbidden();

        $this->get('/admin/resource/moon-shine-user-role-resource/moon-shine-user-role-index-page')
            ->assertForbidden();
    }

    public function test_admin_can_manage_system_roles(): void
    {
        $this->actingAs(MoonshineUser::factory()->create(), 'moonshine')
            ->getJson('/admin/resource/moon-shine-user-role-resource/crud')
            ->assertOk();
    }
}
