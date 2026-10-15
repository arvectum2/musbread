<?php

namespace Tests\Feature;

use App\Models\MuseumEntry;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Tests\TestCase;

class MuseumEntryModelTest extends TestCase
{
    use RefreshDatabase;

    private function entry(string $type, string $slug, string $status = 'draft', ?string $publishTime = null): MuseumEntry
    {
        return MuseumEntry::create([
            'type' => $type, 'slug' => $slug, 'title' => 'Тестовый материал',
            'excerpt' => 'Краткая информация', 'body' => 'Тестовый текст', 'status' => $status,
            'published_at' => $publishTime,
            'seo_title' => 'SEO заголовок', 'seo_description' => 'SEO описание',
            'sort_order' => 10,
        ]);
    }

    public function test_all_supported_types_have_schema_and_can_be_stored(): void
    {
        foreach (array_keys(MuseumEntry::TYPES) as $type) {
            $this->entry($type, 'example-'.$type);
        }
        $this->assertSame(count(MuseumEntry::TYPES), MuseumEntry::count());
        $this->assertSame(1, MuseumEntry::ofType('news')->count());
    }

    public function test_drafts_and_future_publications_never_appear_in_public_query(): void
    {
        $this->entry('page', 'draft', 'draft');
        $this->entry('news', 'later', 'published', now()->addDays(3)->toDateTimeString());
        $this->entry('excursion', 'ready', 'published');
        $this->assertEqualsCanonicalizing(['ready'], MuseumEntry::public()->pluck('slug')->all());
    }

    public function test_seo_metadata_and_published_time_round_trip(): void
    {
        $entry = $this->entry('page', 'seo-check', 'published');
        $entry->refresh();
        $this->assertSame('SEO описание', $entry->seo_description);
        $this->assertSame('SEO заголовок', $entry->seo_title);
        $this->assertNotNull($entry->published_at);
    }
}
