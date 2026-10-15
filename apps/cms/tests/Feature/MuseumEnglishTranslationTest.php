<?php

namespace Tests\Feature;

use App\Models\MuseumEntry;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Tests\TestCase;

class MuseumEnglishTranslationTest extends TestCase
{
    use RefreshDatabase;

    private function export(string $suffix): array
    {
        $out = storage_path('framework/testing/i18n-'.$suffix.'.json');
        $manifest = storage_path('framework/testing/i18n-'.$suffix.'-manifest.json');
        try {
            $this->artisan('museum:export', [
                '--output' => $out, '--manifest' => $manifest,
            ])->assertSuccessful();
            return json_decode(file_get_contents($out), true, flags: JSON_THROW_ON_ERROR);
        } finally {
            @unlink($out);
            @unlink($manifest);
        }
    }

    public function test_incomplete_english_translation_does_not_enter_public_export(): void
    {
        MuseumEntry::create([
            'type' => 'news', 'slug' => 'english-pending',
            'title' => 'Русская новость',
            'body' => 'Русский текст',
            'status' => 'published', 'title_en' => 'Incomplete English',
        ]);
        $snapshot = $this->export('incomplete');
        $this->assertArrayNotHasKey('translations', $snapshot['entries'][0]);
        $this->assertStringNotContainsString('Incomplete English',
            json_encode($snapshot, JSON_UNESCAPED_UNICODE));
    }

    public function test_complete_translation_is_sanitized_and_exported_only_with_published_article(): void
    {
        $entry = MuseumEntry::create([
            'type' => 'news', 'slug' => 'english-complete',
            'title' => 'Русская новость',
            'body' => '<p>Русский текст</p>',
            'status' => 'published',
            'title_en' => 'English test story',
            'excerpt_en' => 'Test description',
            'body_en' => '<p>Safe English paragraph</p><script>alert(1)</script>',
            'seo_title_en' => 'Museum English SEO Title',
            'seo_description_en' => 'English metadata',
        ]);
        $snapshot = $this->export('complete');
        $translation = $snapshot['entries'][0]['translations']['en'];
        $this->assertSame('English test story', $translation['title']);
        $this->assertSame('Museum English SEO Title', $translation['seo_title']);
        $this->assertStringContainsString('Safe English paragraph', $translation['body']);
        $this->assertStringNotContainsString('<script', $translation['body']);
        $this->assertStringNotContainsString('alert(1)', $translation['body']);

        $entry->update(['status' => 'draft']);
        $hidden = $this->export('withdrawn');
        $this->assertCount(0, $hidden['entries']);
    }
}
