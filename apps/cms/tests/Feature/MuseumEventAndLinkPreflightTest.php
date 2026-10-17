<?php

namespace Tests\Feature;

use App\Models\MuseumEntry;
use App\Models\MuseumEvent;
use App\Models\MuseumSection;
use App\Support\MuseumContentPreflight;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Storage;
use MoonShine\Laravel\Models\MoonshineUser;
use MoonShine\Laravel\Models\MoonshineUserRole;
use Tests\TestCase;

class MuseumEventAndLinkPreflightTest extends TestCase
{
    use RefreshDatabase;

    private function entry(string $slug, string $type = 'news', string $status = 'published', ?int $sectionId = null): MuseumEntry
    {
        return MuseumEntry::create([
            'slug' => $slug, 'type' => $type, 'status' => $status,
            'title' => $slug, 'body' => '<p>Содержательное описание.</p>',
            'excerpt' => 'Анонс', 'museum_section_id' => $sectionId,
        ]);
    }

    private function event(string $slug, string $status = 'published'): MuseumEvent
    {
        return MuseumEvent::create([
            'slug' => $slug, 'title' => 'Событие '.$slug,
            'category' => 'Экскурсия', 'starts_at' => now()->addWeek()->toDateString(),
            'excerpt' => 'Анонс события', 'body' => 'Описание события',
            'status' => $status,
        ]);
    }

    private function entryRow(MuseumEntry $entry): array
    {
        return collect(app(MuseumContentPreflight::class)->report()['records'])->firstWhere('id', $entry->id);
    }

    private function eventRow(MuseumEvent $event): array
    {
        return collect(app(MuseumContentPreflight::class)->report()['events'])->firstWhere('id', $event->id);
    }

    private function codes(array $row): array
    {
        return array_column($row['issues'], 'code');
    }

    public function test_event_report_states_and_severity_are_read_only(): void
    {
        $draft = $this->event('draft-event', 'draft');
        $scheduled = $this->event('scheduled-event');
        $scheduled->update(['published_at' => now()->addDay()]);
        $ready = $this->event('ready-event');
        $past = $this->event('past-event');
        $past->update(['starts_at' => now()->subDays(2)->toDateString()]);
        DB::table('museum_events')->where('id', $ready->id)->update([
            'title' => '', 'category' => '',
            'excerpt' => '<p>&nbsp;</p>', 'body' => '<p> </p>', 'slug' => 'BAD slug',
        ]);
        $report = app(MuseumContentPreflight::class)->report();
        $this->assertSame(4, $report['events_total']);
        $this->assertSame(2, $report['events_ready']);
        $this->assertSame('draft', $this->eventRow($draft)['state']);
        $this->assertSame('scheduled', $this->eventRow($scheduled)['state']);
        $this->assertSame('ready', $this->eventRow($ready)['state']);
        foreach (['event_title_missing', 'event_slug_invalid', 'event_category_missing',
            'event_excerpt_missing', 'event_body_missing'] as $code) {
            $this->assertContains($code, $this->codes($this->eventRow($ready)));
        }
        $this->assertContains('event_past', $this->codes($this->eventRow($past)));
        $this->assertGreaterThanOrEqual(5, $report['event_errors']);
        $this->artisan('museum:preflight', ['--strict' => true])->assertFailed();
        $this->assertSame('', $ready->fresh()->title); // no mutation by preflight
    }

    public function test_invalid_event_date_range_is_a_critical_preflight_error(): void
    {
        $event = $this->event('invalid-end-range');
        $event->update(['starts_at' => '2026-11-20', 'ends_at' => '2026-11-18']);
        $row = $this->eventRow($event);
        $this->assertContains('event_date_range_invalid', $this->codes($row));
        $this->artisan('museum:preflight', ['--strict' => true])->assertFailed();
        $event->update(['ends_at' => '2026-11-25']);
        $this->assertNotContains('event_date_range_invalid', $this->codes($this->eventRow($event)));
        $this->artisan('museum:preflight', ['--strict' => true])->assertSuccessful();
    }

    public function test_strict_export_stops_before_writing_for_ready_event_but_not_future_event(): void
    {
        $ready = $this->event('missing-description');
        $future = $this->event('future-draft', 'draft');
        DB::table('museum_events')->where('id', $future->id)->update(['body' => '']);
        $output = storage_path('framework/testing/cp43-export.json');
        $manifest = storage_path('framework/testing/cp43-export-manifest.json');
        file_put_contents($output, 'sentinel: original snapshot');
        file_put_contents($manifest, 'sentinel: original manifest');
        try {
            $this->artisan('museum:preflight', ['--strict' => true])->assertSuccessful();
            DB::table('museum_events')->where('id', $ready->id)->update(['body' => '']);
            $this->artisan('museum:export', [
                '--preflight-strict' => true, '--output' => $output, '--manifest' => $manifest,
            ])->assertFailed();
            $this->assertSame('sentinel: original snapshot', file_get_contents($output));
            $this->assertSame('sentinel: original manifest', file_get_contents($manifest));
            DB::table('museum_events')->where('id', $ready->id)->update(['body' => 'Детали восстановлены']);
            $this->artisan('museum:export', [
                '--preflight-strict' => true, '--output' => $output, '--manifest' => $manifest,
            ])->assertSuccessful();
            $result = json_decode(file_get_contents($output), true, flags: JSON_THROW_ON_ERROR);
            $this->assertSame('missing-description', $result['events'][0]['slug']);
            $this->assertCount(1, $result['events']);
        } finally {
            @unlink($output);
            @unlink($manifest);
        }
    }

    public function test_internal_links_to_ready_draft_future_and_hidden_targets(): void
    {
        $ready = $this->entry('available-target');
        $draft = $this->entry('draft-target', 'news', 'draft');
        $future = $this->entry('scheduled-target');
        $future->update(['published_at' => now()->addDay()]);
        $hiddenSection = MuseumSection::create(['slug' => 'hidden', 'title' => 'Тайный раздел', 'status' => 'draft']);
        $hidden = $this->entry('hidden-target', 'news', 'published', $hiddenSection->id);
        $event = $this->event('available-event');
        $draftEvent = $this->event('draft-event', 'draft');
        $source = $this->entry('source-news');
        $source->update(['body' => '<p>Проверка ссылок</p>'
            .'<a href="/news/'.$ready->slug.'/?from=qa#abc">Действующая</a>'
            .'<a href="/events/'.$event->slug.'/">Событие</a>'
            .'<a href="/news/'.$draft->slug.'/">Черновик</a>'
            .'<a href="/news/'.$future->slug.'/">Ожидание даты</a>'
            .'<a href="/news/'.$hidden->slug.'/">Скрытая ветка</a>'
            .'<a href="/events/'.$draftEvent->slug.'/">Скрытое событие</a>'
            .'<a href="/news/not-in-database/">Удалено</a>'
            .'<a href="/news/not-in-database/?x=1">Дубль удалённого</a>'
            .'<a href="https://example.org/news/outside/">Внешний</a>'
            .'<a href="#citation">Ссылка на якорь</a>'
            .'<a href="/news/">Индекс</a>']);
        $issues = $this->entryRow($source)['issues'];
        $matches = array_filter($issues, static fn ($issue) => $issue['code'] === 'internal_link_unavailable');
        $this->assertCount(5, $matches);
        $this->assertNotContains('internal_link_invalid', $this->codes($this->entryRow($source)));
        $this->assertSame(5, app(MuseumContentPreflight::class)->report()['errors']);
    }

    public function test_relative_and_english_routes_and_type_mismatch_are_checked(): void
    {
        $other = $this->entry('other', 'excursion');
        $english = $this->entry('translated');
        $english->update(['title_en' => 'Museum news', 'body_en' => '<p>English text</p>']);
        $source = $this->entry('original');
        $source->update(['body' => '<p>Ссылки</p>'
            .'<a href="../translated/">Соседняя новость</a>'
            .'<a href="/en/news/translated/">Английская</a>'
            .'<a href="/excursions/other/">Экскурсия</a>'
            .'<a href="/news/other/">Неправильный тип</a>'
            .'<a href="/en/news/original/">Не существует английской версии</a>'
            .'<a href="/news/bad name/">Неверный slug</a>']);
        $codes = $this->codes($this->entryRow($source));
        $this->assertSame(2, count(array_filter($codes, static fn ($code) => $code === 'internal_link_unavailable')));
        $this->assertContains('internal_link_invalid', $codes);
        $this->assertSame(3, app(MuseumContentPreflight::class)->report()['errors']);
    }

    public function test_event_links_and_hidden_target_warnings_do_not_expose_private_editorial_data(): void
    {
        $ownSection = MuseumSection::create(['slug' => 'own', 'title' => 'Своя секция', 'status' => 'published']);
        $secretSection = MuseumSection::create(['slug' => 'secret', 'title' => 'СЕКРЕТНО', 'status' => 'draft']);
        $source = $this->entry('owned-page', 'news', 'draft', $ownSection->id);
        $secret = $this->entry('unreleased-secret', 'news', 'draft', $secretSection->id);
        $event = $this->event('exhibition-link');
        $event->update(['museum_section_id' => $ownSection->id]);
        $event->relatedEntries()->attach($secret->id);
        $event->update(['body' => '<p>Открытые даты</p><a href="/news/unreleased-secret/">Ссылка</a>']);
        $role = MoonshineUserRole::query()->where('name', 'Editor')->firstOrFail();
        $editor = MoonshineUser::factory()->create(['moonshine_user_role_id' => $role->id]);
        $ownSection->editors()->attach($editor->id);
        $this->actingAs($editor, 'moonshine');
        $this->get('/admin/resource/museum-event-resource/museum-event-index-page')
            ->assertOk()->assertSee(route('museum.content.preflight').'#event-'.$event->id, false);
        $this->get(route('museum.content.preflight'))->assertOk()
            ->assertSee('exhibition-link')->assertSee('owned-page')
            ->assertDontSee('СЕКРЕТНО')->assertDontSee('unreleased-secret');
        $report = app(MuseumContentPreflight::class)->report($editor);
        $this->assertSame(1, $report['total']);
        $this->assertSame(1, $report['events_total']);
        $this->assertContains('internal_link_unavailable', $this->codes($report['events'][0]));
        $this->assertContains('event_relation_unpublished', $this->codes($report['events'][0]));
    }

    public function test_partial_english_translation_never_blocks_russian_export(): void
    {
        $source = $this->entry('russian-only');
        $source->update(['title_en' => null,
            'body_en' => '<p>Unpublished English draft <a href="/en/news/missing/">Bad</a></p>']);
        $row = $this->entryRow($source);
        $this->assertContains('translation_incomplete', $this->codes($row));
        $this->assertNotContains('internal_link_unavailable', $this->codes($row));
        $this->artisan('museum:preflight', ['--strict' => true])->assertSuccessful();
    }

    public function test_document_and_image_internal_links_match_exported_asset_hashes(): void
    {
        Storage::fake('local');
        $owner = $this->entry('assets-owner');
        $documentBytes = 'Synthetic PDF content';
        $docHash = hash('sha256', $documentBytes);
        $imageBytes = 'Synthetic image content';
        $imageHash = hash('sha256', $imageBytes);
        Storage::disk('local')->put('museum/documents/internal-test.pdf', $documentBytes);
        Storage::disk('local')->put('museum/images/internal-test.webp', $imageBytes);
        DB::table('museum_documents')->insert([
            'museum_entry_id' => $owner->id, 'label' => 'Публичный файл',
            'file_type' => 'pdf', 'storage_path' => 'museum/documents/internal-test.pdf',
            'sha256' => $docHash, 'size_bytes' => strlen($documentBytes),
            'created_at' => now(), 'updated_at' => now(),
        ]);
        DB::table('museum_media')->insert([
            'museum_entry_id' => $owner->id, 'storage_path' => 'museum/images/internal-test.webp',
            'sha256' => $imageHash, 'alt' => 'Экспонат', 'mime' => 'image/webp',
            'width' => 10, 'height' => 10, 'size_bytes' => strlen($imageBytes),
            'created_at' => now(), 'updated_at' => now(),
        ]);
        $source = $this->entry('assets-source');
        $source->update(['body' => '<p>Файлы</p>'
            .'<a href="/documents/'.$docHash.'.pdf">Документ</a>'
            .'<a href="/media/'.$imageHash.'.webp">Картинка</a>'
            .'<a href="/documents/'.str_repeat('b', 64).'.pdf">Старый документ</a>'
            .'<a href="/media/'.str_repeat('c', 64).'.webp">Старая картинка</a>']);
        $codes = $this->codes($this->entryRow($source));
        $this->assertSame(2, count(array_filter($codes,
            static fn ($code) => $code === 'internal_asset_unavailable')));
        $this->assertNotContains('internal_link_invalid', $codes);
    }

    public function test_event_missing_seo_is_warning_only_and_cli_json_includes_events(): void
    {
        $this->event('seo-later');
        $report = app(MuseumContentPreflight::class)->report();
        $this->assertSame(0, $report['event_errors']);
        $this->assertSame(1, $report['events_total']);
        $this->assertContains('event_seo_title_missing', $this->codes($report['events'][0]));
        $this->artisan('museum:preflight', ['--strict' => true])->assertSuccessful();
        $this->assertSame(0, \Artisan::call('museum:preflight', ['--json' => true]));
        $json = json_decode(trim(\Artisan::output()), true, flags: JSON_THROW_ON_ERROR);
        $this->assertSame('seo-later', $json['events'][0]['slug']);
    }
}
