<?php

namespace Tests\Feature;

use App\Models\MuseumEntry;
use App\Models\MuseumEvent;
use App\Models\MuseumSection;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Tests\TestCase;

class MuseumContentRelationsExportTest extends TestCase
{
    use RefreshDatabase;

    private function entry(string $slug, string $type, string $status = 'published', ?int $section = null): MuseumEntry
    {
        return MuseumEntry::create([
            'slug' => $slug, 'title' => 'Тест '.$slug,
            'type' => $type, 'body' => 'Информация '.$slug, 'status' => $status,
            'museum_section_id' => $section,
        ]);
    }

    private function event(string $slug, string $status = 'published', ?string $time = null): MuseumEvent
    {
        return MuseumEvent::create([
            'slug' => $slug, 'title' => 'Событие '.$slug, 'category' => 'Афиша',
            'starts_at' => '2026-11-20', 'body' => 'Текст события', 'excerpt' => 'Анонс',
            'status' => $status, 'published_at' => $time,
        ]);
    }

    private function export(string $name): array
    {
        $out = storage_path('framework/testing/linked-'.$name.'.json');
        $manifest = storage_path('framework/testing/linked-'.$name.'-manifest.json');
        try {
            $this->artisan('museum:export', ['--output' => $out, '--manifest' => $manifest])
                ->assertSuccessful();
            $raw = file_get_contents($out);
            $audit = json_decode(file_get_contents($manifest), true, flags: JSON_THROW_ON_ERROR);
            $this->assertSame(hash('sha256', $raw), $audit['files']['published.json']['sha256']);
            return [json_decode($raw, true, flags: JSON_THROW_ON_ERROR), $raw];
        } finally {
            @unlink($out);
            @unlink($manifest);
        }
    }

    public function test_export_links_only_approved_content_and_reverse_event_links(): void
    {
        $approved = MuseumSection::create(['slug' => 'visible', 'title' => 'Доступен', 'status' => 'published']);
        $blocked = MuseumSection::create(['slug' => 'not-ready', 'title' => 'Закрыт', 'status' => 'draft']);
        $root = $this->entry('source-exhibition', 'exhibition', 'published', $approved->id);
        $excursion = $this->entry('guided-tour', 'excursion', 'published', $approved->id);
        $document = $this->entry('visitor-rules', 'document', 'published', $approved->id);
        $draft = $this->entry('hidden-secret', 'news', 'draft', $approved->id);
        $scheduled = $this->entry('scheduled-secret', 'news', 'published', $approved->id);
        $scheduled->update(['published_at' => now()->addDays(7)]);
        $hiddenSection = $this->entry('hidden-section-page', 'page', 'published', $blocked->id);
        $visibleEvent = $this->event('visible-event');
        $privateEvent = $this->event('secret-event', 'draft');
        $futureEvent = $this->event('future-event', 'published', now()->addDays(8)->toDateTimeString());

        $root->relatedEntries()->attach([
            $excursion->id, $document->id, $draft->id, $scheduled->id, $hiddenSection->id,
        ]);
        $root->linkedEvents()->attach([$visibleEvent->id, $privateEvent->id, $futureEvent->id]);
        $draft->linkedEvents()->attach($visibleEvent->id);
        $hiddenSection->linkedEvents()->attach($visibleEvent->id);
        [$data, $raw] = $this->export('approved');
        $published = collect($data['entries'])->firstWhere('slug', 'source-exhibition');
        $this->assertNotNull($published);
        $this->assertEqualsCanonicalizing(
            ['/excursions/guided-tour/', '/documents/visitor-rules/'],
            array_column($published['related_entries'], 'href')
        );
        $this->assertSame(['href', 'title', 'type'], array_keys($published['related_entries'][0]));
        $this->assertSame(['/events/visible-event/'], array_column($published['related_events'], 'href'));
        $event = collect($data['events'])->firstWhere('slug', 'visible-event');
        $this->assertSame(['/exhibitions/source-exhibition/'], array_column($event['related_entries'], 'href'));
        foreach (['hidden-secret', 'scheduled-secret', 'hidden-section-page',
            'secret-event', 'future-event', 'uploaded_by', 'museum_entry_id', 'source_entry_id'] as $private) {
            $this->assertStringNotContainsString($private, $raw);
        }
        $this->assertCount(1, $data['events']);
        $this->assertCount(3, $data['entries']);

        // Changing the public state withdraws the relationship without touching
        // the private editorial graph. It can safely return after reapproval.
        $excursion->update(['status' => 'draft']);
        $visibleEvent->update(['status' => 'draft']);
        [$after] = $this->export('withdrawn');
        $publicRoot = collect($after['entries'])->firstWhere('slug', 'source-exhibition');
        $this->assertSame(['/documents/visitor-rules/'], array_column($publicRoot['related_entries'], 'href'));
        $this->assertArrayNotHasKey('related_events', $publicRoot);
        $this->assertEmpty($after['events']);
        $this->assertSame(5, $root->relatedEntries()->count());
    }

    public function test_existing_exports_without_relations_keep_original_schema(): void
    {
        $entry = $this->entry('standalone', 'page');
        $event = $this->event('standalone-event');
        [$data] = $this->export('empty');
        $this->assertArrayNotHasKey('related_entries', $data['entries'][0]);
        $this->assertArrayNotHasKey('related_events', $data['entries'][0]);
        $this->assertArrayNotHasKey('related_entries', $data['events'][0]);
        $this->assertSame('standalone', $data['entries'][0]['slug']);
        $this->assertSame('standalone-event', $data['events'][0]['slug']);
    }
}
