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

    public function test_default_mit_jodit_mode_loads_self_hosted_wysiwyg_and_source(): void
    {
        config()->set('museum.entry_body_editor', 'jodit');
        $response = $this->actingAs(MoonshineUser::factory()->create(), 'moonshine')
            ->get('/admin/resource/museum-entry-resource/museum-entry-form-page');
        $response->assertOk();
        $response->assertSee('vendor/museum-jodit/jodit.min.js', false)
            ->assertSee('vendor/museum-jodit/jodit.min.css', false)
            ->assertSee('vendor/museum-jodit/museum-jodit-init.js', false)
            ->assertSee('data-museum-jodit', false)
            ->assertDontSee('vendor/moonshine-tinymce/', false)
            ->assertDontSee('cdn.tiny.cloud', false)
            ->assertDontSee('license_key', false);
    }

    public function test_unsupported_editor_mode_fails_closed(): void
    {
        config()->set('museum.entry_body_editor', 'unsupported');
        $this->actingAs(MoonshineUser::factory()->create(), 'moonshine')
            ->get('/admin/resource/museum-entry-resource/museum-entry-form-page')
            ->assertStatus(500);
    }

    public function test_jodit_source_code_mode_never_bypasses_server_html_policy():void
    {
        config()->set('museum.entry_body_editor','jodit');
        $this->actingAs(MoonshineUser::factory()->create(),'moonshine')
            ->post('/admin/resource/museum-entry-resource/crud',[
                'type'=>'news','slug'=>'html-modal-malicious','title'=>'HTML modal XSS test',
                'body'=>'<p><strong>Безопасный текст</strong>'
                    .'<a href="javascript:alert(2)" onclick="alert(3)">Опасная ссылка</a></p>'
                    .'<h2>Подзаголовок</h2><ol><li>Элемент списка</li></ol>'
                    .'<iframe src="https://malicious.invalid/"></iframe>'
                    .'<script>alert(1)</script>',
                'status'=>'draft',
            ])->assertRedirect();
        $html=MuseumEntry::where('slug','html-modal-malicious')->firstOrFail()->body;
        foreach(['<script','<iframe','javascript:','onclick='] as $forbidden)
            $this->assertStringNotContainsString($forbidden,$html);
        foreach(['<strong>Безопасный текст</strong>','<h2>Подзаголовок</h2>',
                 '<ol>','<li>Элемент списка</li>'] as $expected)
            $this->assertStringContainsString($expected,$html);
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
