<?php

namespace Tests\Feature;

use App\Models\MuseumEntry;
use Illuminate\Foundation\Testing\RefreshDatabase;
use MoonShine\Laravel\Models\MoonshineUser;
use Tests\TestCase;

class MuseumEntryEditorTest extends TestCase
{
    use RefreshDatabase;

    public function test_authenticated_admin_can_create_page_through_moonshine(): void
    {
        $this->actingAs(MoonshineUser::factory()->create(), 'moonshine')
            ->get('/admin/resource/museum-entry-resource/museum-entry-form-page')
            ->assertOk();

        $this->post('/admin/resource/museum-entry-resource/crud', [
            'type' => 'page', 'title' => 'История музея', 'slug' => 'museum-history',
            'body' => 'Предварительный материал', 'status' => 'draft',
            'seo_title' => 'История музея — тест',
        ])->assertRedirect();

        $this->assertDatabaseHas('museum_entries', [
            'type' => 'page', 'slug' => 'museum-history', 'status' => 'draft',
            'seo_title' => 'История музея — тест',
        ]);
        $this->assertSame(0, MuseumEntry::public()->count());
    }

    public function test_sql_injection_like_slug_is_rejected_before_persistence(): void
    {
        $this->actingAs(MoonshineUser::factory()->create(), 'moonshine')
            ->post('/admin/resource/museum-entry-resource/crud', [
                'type' => 'news',
                'title' => 'SQL injection smoke',
                'slug' => "x' OR 1=1--",
                'body' => 'Placeholder',
                'status' => 'draft',
            ])->assertRedirect();

        $this->assertSame(0, MuseumEntry::count());
    }

    public function test_invalid_type_cannot_be_published_from_moonshine(): void
    {
        $this->actingAs(MoonshineUser::factory()->create(), 'moonshine')
            ->post('/admin/resource/museum-entry-resource/crud', [
                'type' => 'unknown', 'title' => 'Ошибка', 'slug' => 'invalid',
                'body' => 'Тест', 'status' => 'published',
            ])->assertRedirect();
        $this->assertSame(0, MuseumEntry::count());
    }
}
