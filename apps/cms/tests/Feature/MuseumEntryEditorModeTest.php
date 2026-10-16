<?php

namespace Tests\Feature;

use App\Models\MuseumEntry;
use Illuminate\Foundation\Testing\RefreshDatabase;
use MoonShine\Laravel\Models\MoonshineUser;
use Tests\TestCase;

class MuseumEntryEditorModeTest extends TestCase
{
    use RefreshDatabase;

    public function test_html_source_fallback_uses_escaped_native_textarea_without_tinymce_assets(): void
    {
        config()->set('museum.entry_body_editor', 'html-source');
        $response = $this->actingAs(MoonshineUser::factory()->create(), 'moonshine')
            ->get('/admin/resource/museum-entry-resource/museum-entry-form-page');
        $response->assertOk();
        $response->assertSee('Основной текст (HTML-код', false);
        $response->assertDontSee('vendor/moonshine-tinymce/tinymce.min.js', false);
        $response->assertDontSee('license_key', false);
    }

    public function test_default_tinymce_mode_still_uses_the_existing_rich_editor(): void
    {
        config()->set('museum.entry_body_editor', 'tinymce');
        $response = $this->actingAs(MoonshineUser::factory()->create(), 'moonshine')
            ->get('/admin/resource/museum-entry-resource/museum-entry-form-page');
        $response->assertOk();
        $response->assertSee('vendor/moonshine-tinymce/tinymce.min.js', false);
    }

    public function test_unsupported_editor_mode_fails_closed(): void
    {
        config()->set('museum.entry_body_editor', 'unsupported');
        $this->actingAs(MoonshineUser::factory()->create(), 'moonshine')
            ->get('/admin/resource/museum-entry-resource/museum-entry-form-page')
            ->assertStatus(500);
    }

    public function test_plain_html_mode_preserves_server_side_sanitization(): void
    {
        config()->set('museum.entry_body_editor', 'html-source');
        $this->actingAs(MoonshineUser::factory()->create(), 'moonshine')
            ->post('/admin/resource/museum-entry-resource/crud', [
                'type' => 'news',
                'slug' => 'html-source-safety',
                'title' => 'Тест HTML',
                'body' => '<p>Безопасный текст</p><script>alert(1)</script>',
                'status' => 'draft',
            ])->assertRedirect();
        $entry=MuseumEntry::where('slug','html-source-safety')->firstOrFail();
        $this->assertStringContainsString('Безопасный текст', $entry->body);
        $this->assertStringNotContainsString('<script', $entry->body);
    }
}
