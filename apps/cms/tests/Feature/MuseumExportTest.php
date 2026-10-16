<?php

namespace Tests\Feature;

use App\Models\MuseumEvent;
use App\Models\MuseumEntry;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Tests\TestCase;

class MuseumExportTest extends TestCase
{
    use RefreshDatabase;

    public function test_static_export_includes_approved_entries_but_never_drafts(): void
    {
        $base = ['type' => 'news', 'title' => 'Тестовая новость',
            'body' => 'Открытый тестовый текст', 'excerpt' => 'Анонс',
            'seo_title' => 'Тестовый SEO title'];
        MuseumEntry::create(array_merge($base, [
            'slug' => 'draft-news', 'status' => 'draft',
        ]));
        MuseumEntry::create(array_merge($base, [
            'slug' => 'public-news', 'status' => 'published',
            'published_at' => now()->subDay(),
        ]));

        $out = storage_path('framework/testing/entries.json');
        $manifest = storage_path('framework/testing/entries-manifest.json');
        $this->artisan('museum:export', ['--output' => $out, '--manifest' => $manifest])
            ->assertSuccessful();
        $data = json_decode(file_get_contents($out), true, flags: JSON_THROW_ON_ERROR);
        $this->assertCount(1, $data['entries']);
        $this->assertSame('public-news', $data['entries'][0]['slug']);
        $this->assertSame('Тестовый SEO title', $data['entries'][0]['seo_title']);
        $this->assertStringNotContainsString('draft-news', file_get_contents($out));
        $audit = json_decode(file_get_contents($manifest), true, flags: JSON_THROW_ON_ERROR);
        $this->assertSame(1, $audit['entry_count']);
        $this->assertSame(hash_file('sha256', $out), $audit['files']['published.json']['sha256']);
        unlink($out);
        unlink($manifest);
    }

    public function test_multiday_event_is_exported_with_end_date_without_leaking_unpublished_records(): void
    {
        MuseumEvent::create([
            'slug' => 'multiday-exhibition', 'title' => 'Несколько дней', 'category' => 'Выставка',
            'starts_at' => '2026-11-05', 'ends_at' => '2026-11-19',
            'status' => 'published', 'published_at' => now()->subDay(),
            'excerpt' => 'Анонс', 'body' => 'Программа',
        ]);
        MuseumEvent::create([
            'slug' => 'hidden-exhibition', 'title' => 'Скрыто', 'category' => 'Выставка',
            'starts_at' => '2026-11-05', 'ends_at' => '2026-11-19',
            'status' => 'draft', 'excerpt' => 'Анонс', 'body' => 'Программа',
        ]);
        $out = storage_path('framework/testing/event-range.json');
        $manifest = storage_path('framework/testing/event-range-manifest.json');
        try {
            $this->artisan('museum:export', ['--output' => $out, '--manifest' => $manifest])->assertSuccessful();
            $data = json_decode(file_get_contents($out), true, flags: JSON_THROW_ON_ERROR);
            $this->assertCount(1, $data['events']);
            $this->assertSame('2026-11-05', $data['events'][0]['date']);
            $this->assertSame('2026-11-19', $data['events'][0]['ends_on']);
            $this->assertStringNotContainsString('hidden-exhibition', file_get_contents($out));
        } finally {
            @unlink($out); @unlink($manifest);
        }
    }

    public function test_only_approved_records_leave_the_private_cms(): void
    {
        $fixture = [
            'title' => 'Example', 'category' => 'Test', 'starts_at' => '2026-11-17',
            'excerpt' => 'Excerpt', 'body' => 'Description',
        ];
        MuseumEvent::create(array_merge($fixture, [
            'slug' => 'private-draft', 'status' => 'draft',
        ]));
        MuseumEvent::create(array_merge($fixture, [
            'slug' => 'future-private', 'status' => 'published',
            'published_at' => now()->addDay(),
        ]));
        MuseumEvent::create(array_merge($fixture, [
            'slug' => 'public-event', 'status' => 'published',
            'published_at' => now()->subDay(),
        ]));

        $out = storage_path('framework/testing/snapshot.json');
        $manifest = storage_path('framework/testing/manifest.json');
        $this->artisan('museum:export', ['--output' => $out, '--manifest' => $manifest])->assertSuccessful();
        $data = json_decode(file_get_contents($out), true, flags: JSON_THROW_ON_ERROR);
        $this->assertCount(1, $data['events']);
        $this->assertSame('public-event', $data['events'][0]['slug']);
        $this->assertStringNotContainsString('private-draft', file_get_contents($out));
        $this->assertStringNotContainsString('future-private', file_get_contents($out));
        $audit = json_decode(file_get_contents($manifest), true, flags: JSON_THROW_ON_ERROR);
        $this->assertSame(hash_file('sha256', $out), $audit['files']['published.json']['sha256']);
        unlink($out);
        unlink($manifest);
    }
}
