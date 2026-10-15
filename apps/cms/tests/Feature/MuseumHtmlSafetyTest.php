<?php

namespace Tests\Feature;

use App\Models\MuseumEntry;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Tests\TestCase;

class MuseumHtmlSafetyTest extends TestCase
{
    use RefreshDatabase;

    public function test_public_body_preserves_safe_markup_but_removes_scripts_and_event_handlers(): void
    {
        $entry = MuseumEntry::create([
            'type' => 'page', 'slug' => 'safe-html',
            'title' => 'HTML текст', 'status' => 'published',
            'body' => '<h2>Заголовок</h2><p><strong>Смысл</strong> и <a href="javascript:alert(1)" onclick="evil()">ссылка</a></p><script>alert(2)</script><img src=x onerror=evil()>',
        ]);
        $entry->refresh();
        $this->assertStringContainsString('<h2>Заголовок</h2>', $entry->body);
        $this->assertStringContainsString('<strong>Смысл</strong>', $entry->body);
        $this->assertStringNotContainsString('javascript:', $entry->body);
        $this->assertStringNotContainsString('onclick', $entry->body);
        $this->assertStringNotContainsString('<script', $entry->body);
        $this->assertStringNotContainsString('<img', $entry->body);
    }

    public function test_export_contains_only_sanitized_rich_text(): void
    {
        MuseumEntry::create([
            'type' => 'page', 'slug' => 'export-safe', 'title' => 'Безопасная страница',
            'status' => 'published', 'body' => '<p onclick="evil()">Сохранённый текст</p><script>attack()</script>',
        ]);

        $out = storage_path('framework/testing/safe-rich-text.json');
        $manifest = storage_path('framework/testing/safe-rich-text-manifest.json');
        try {
            $this->artisan('museum:export', ['--output' => $out, '--manifest' => $manifest])
                ->assertSuccessful();
            $text = file_get_contents($out);
            $this->assertStringContainsString('<p>Сохранённый текст</p>', $text);
            $this->assertStringNotContainsString('onclick', $text);
            $this->assertStringNotContainsString('attack()', $text);
        } finally {
            @unlink($out);
            @unlink($manifest);
        }
    }

    public function test_disallowed_embed_is_removed_on_edit(): void
    {
        $entry = MuseumEntry::create([
            'type' => 'news', 'slug' => 'edited', 'title' => 'Новость',
            'body' => 'До редактирования', 'status' => 'draft',
        ]);
        $entry->body = '<p>После редактирования</p><iframe src="https://evil.example"></iframe>';
        $entry->save();
        $this->assertSame('<p>После редактирования</p>', $entry->fresh()->body);
    }
}
