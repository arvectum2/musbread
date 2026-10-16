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

class MuseumContentPreflightTest extends TestCase
{
    use RefreshDatabase;

    private function section(string $slug, string $status = 'published', ?int $parent = null): MuseumSection
    {
        return MuseumSection::create([
            'slug' => $slug, 'title' => 'Рубрика '.$slug, 'status' => $status, 'parent_id' => $parent,
        ]);
    }

    private function entry(string $slug, string $status = 'draft', ?int $sectionId = null,
        string $type = 'news', ?string $body = '<p>Текст публикации</p>'): MuseumEntry
    {
        return MuseumEntry::create([
            'type' => $type, 'slug' => $slug, 'title' => 'Заголовок '.$slug,
            'body' => $body, 'excerpt' => 'Анонс публикации', 'h1' => 'H1 '.$slug,
            'seo_title' => 'SEO '.$slug, 'seo_description' => 'Мета-описание '.$slug,
            'status' => $status, 'museum_section_id' => $sectionId,
        ]);
    }

    private function codes(array $record): array
    {
        return array_column($record['issues'], 'code');
    }

    private function reportRow(MuseumEntry $entry): array
    {
        return collect(app(MuseumContentPreflight::class)->report()['records'])
            ->firstWhere('id', $entry->id);
    }

    public function test_private_report_is_readonly_and_guest_cannot_read_drafts(): void
    {
        $private = $this->entry('secret-draft');
        $this->get(route('museum.content.preflight'))->assertRedirect('/admin/login')
            ->assertDontSee('secret-draft');
        $this->actingAs(MoonshineUser::factory()->create(), 'moonshine');
        $this->get(route('museum.content.preflight'))->assertOk()
            ->assertSee('secret-draft')
            ->assertSee('Проверка перед публикацией')
            ->assertSee('Исправить в CMS')
            ->assertHeader('X-Robots-Tag', 'noindex, nofollow, noarchive')
            ->assertHeader('Cache-Control', 'max-age=0, no-store, private')
            ->assertHeader('Content-Security-Policy', "default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'");
        $this->get('/admin/resource/museum-entry-resource/museum-entry-index-page')
            ->assertOk()->assertSee(route('museum.content.preflight').'#entry-'.$private->id, false);
        $original = $private->fresh()->toArray();
        $this->artisan('museum:preflight')->assertSuccessful();
        $this->assertEquals($original, $private->fresh()->toArray());
    }

    public function test_editor_receives_only_own_section_and_never_foreign_names_or_issues(): void
    {
        $my = $this->section('permitted');
        $foreign = $this->section('forbidden');
        $mine = $this->entry('visible-to-editor', sectionId: $my->id);
        $hidden = $this->entry('super-secret-material', sectionId: $foreign->id);
        $mine->relatedEntries()->attach($hidden->id);
        $role = MoonshineUserRole::query()->where('name', 'Editor')->firstOrFail();
        $editor = MoonshineUser::factory()->create(['moonshine_user_role_id' => $role->id]);
        $my->editors()->attach($editor->id);
        $this->actingAs($editor, 'moonshine');
        $response = $this->get(route('museum.content.preflight'))->assertOk()
            ->assertSee('visible-to-editor')->assertDontSee('super-secret-material')
            ->assertDontSee('Рубрика forbidden');
        $report = app(MuseumContentPreflight::class)->report($editor);
        $this->assertSame(1, $report['total']);
        $this->assertSame($mine->id, $report['records'][0]['id']);
        // Access checks must also apply to UI entry links inside the report.
        $response->assertDontSee('/museum-entry-form-page/'.$hidden->id, false);
    }

    public function test_severity_readiness_and_optional_missing_fields(): void
    {
        $root = $this->section('draft-parent', 'draft');
        $child = $this->section('child', 'published', $root->id);
        $goodSection = $this->section('open');
        $draft = $this->entry('draft-check', sectionId: $goodSection->id);
        $future = $this->entry('future-check', 'published', $goodSection->id);
        $future->update(['published_at' => now()->addDays(2)]);
        $blocked = $this->entry('blocked-check', 'published', $child->id);
        $ready = $this->entry('ready-check', 'published', $goodSection->id);
        $ready->update(['h1' => null, 'seo_title' => null, 'seo_description' => null,
            'excerpt' => null, 'title_en' => 'Partial translation', 'body_en' => null]);
        DB::table('museum_entries')->where('id', $draft->id)->update(['body' => '<p></p>']);
        $report = app(MuseumContentPreflight::class)->report();
        $states = collect($report['records'])->pluck('state', 'slug');
        $this->assertSame('draft', $states['draft-check']);
        $this->assertSame('scheduled', $states['future-check']);
        $this->assertSame('blocked', $states['blocked-check']);
        $this->assertSame('ready', $states['ready-check']);
        $this->assertSame(1, $report['ready']);
        $this->assertSame(0, $report['errors']);
        $this->assertContains('body_missing', $this->codes($this->reportRow($draft)));
        foreach (['h1_missing', 'seo_title_missing', 'seo_description_missing',
            'excerpt_missing', 'translation_incomplete'] as $warning) {
            $this->assertContains($warning, $this->codes($this->reportRow($ready)));
        }
        $this->artisan('museum:preflight', ['--strict' => true])->assertSuccessful();
    }

    public function test_strict_export_aborts_before_any_write_but_default_remains_compatible(): void
    {
        $ready = $this->entry('bad-content', 'published');
        DB::table('museum_entries')->where('id', $ready->id)->update(['body' => '<p> </p>']);
        $out = storage_path('framework/testing/preflight-sentinel.json');
        $manifest = storage_path('framework/testing/preflight-sentinel-manifest.json');
        file_put_contents($out, 'unchanged public file sentinel');
        file_put_contents($manifest, 'unchanged manifest sentinel');
        try {
            $this->artisan('museum:preflight', ['--strict' => true])->assertFailed();
            $this->artisan('museum:export', [
                '--preflight-strict' => true, '--output' => $out, '--manifest' => $manifest,
            ])->assertFailed();
            $this->assertSame('unchanged public file sentinel', file_get_contents($out));
            $this->assertSame('unchanged manifest sentinel', file_get_contents($manifest));
            $this->artisan('museum:export', ['--output' => $out, '--manifest' => $manifest])
                ->assertSuccessful();
            $this->assertSame('bad-content', json_decode(file_get_contents($out), true)['entries'][0]['slug']);
        } finally {
            @unlink($out);
            @unlink($manifest);
        }
    }

    public function test_documents_media_and_unpublished_relations_are_checked_without_exposing_names(): void
    {
        Storage::fake('local');
        $documentPage = $this->entry('museum-file', 'published', type: 'document');
        $this->assertContains('document_missing', $this->codes($this->reportRow($documentPage)));
        $linked = $this->entry('linked-document', 'published');
        $hidden = $this->entry('top-secret-link');
        $linked->relatedEntries()->attach($hidden->id);
        $event = MuseumEvent::create([
            'slug' => 'future-event', 'title' => 'Запланировано', 'category' => 'Событие',
            'starts_at' => now()->addMonth(), 'body' => 'Детали', 'excerpt' => 'Анонс',
            'status' => 'draft',
        ]);
        $linked->linkedEvents()->attach($event->id);
        $this->assertContains('related_unpublished', $this->codes($this->reportRow($linked)));
        $this->assertStringNotContainsString('top-secret-link', json_encode($this->reportRow($linked)));
        // Test generated records rather than accepting dangerous uploads.
        DB::table('museum_media')->insert([
            'museum_entry_id' => $linked->id, 'storage_path' => 'museum/photos/not-found.webp',
            'sha256' => str_repeat('a', 64), 'alt' => '', 'caption' => null, 'mime' => 'image/webp',
            'width' => 20, 'height' => 20, 'size_bytes' => 100,
            'created_at' => now(), 'updated_at' => now(),
        ]);
        $codes = $this->codes($this->reportRow($linked));
        $this->assertContains('media_alt_missing', $codes);
        $this->assertContains('media_file_missing', $codes);
        $this->assertSame(1, app(MuseumContentPreflight::class)->report()['errors']);
    }

    public function test_nonbreaking_whitespace_only_html_is_a_critical_issue(): void
    {
        $entry = $this->entry('empty-html', 'published');
        DB::table('museum_entries')->where('id', $entry->id)
            ->update(['body' => '<p>&nbsp; &#8239; </p>']);
        $this->assertContains('body_missing', $this->codes($this->reportRow($entry)));
        $this->artisan('museum:preflight', ['--strict' => true])->assertFailed();
    }

    public function test_json_output_is_machine_readable_without_changing_records(): void
    {
        $this->entry('sample-json', 'published');
        $command = \Artisan::call('museum:preflight', ['--json' => true]);
        $this->assertSame(0, $command);
        $data = json_decode(trim(\Artisan::output()), true, flags: JSON_THROW_ON_ERROR);
        $this->assertSame(1, $data['ready']);
        $this->assertSame('sample-json', $data['records'][0]['slug']);
    }
}
