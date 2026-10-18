<?php

declare(strict_types=1);

namespace Tests\Feature;

use App\Models\MuseumEntry;
use App\Models\MuseumSection;
use Database\Seeders\ReferenceMuseumSectionsSeeder;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Artisan;
use Tests\TestCase;

final class ImportOfficialExcursionsTest extends TestCase
{
    use RefreshDatabase;

    public function test_four_source_pages_are_drafts_preserve_editor_changes_and_reimport_is_idempotent(): void
    {
        $this->seed(ReferenceMuseumSectionsSeeder::class);
        $this->assertSame(0, Artisan::call('museum:import-official-excursions'));
        $this->assertDatabaseCount('museum_entries', 0);
        $this->assertSame(0, Artisan::call('museum:import-official-excursions', [
            '--apply' => true,
        ]), Artisan::output());
        $this->assertDatabaseCount('museum_entries', 4);
        foreach (['excursion-overview', 'excursion-interactive', 'excursion-thematic', 'excursion-theatrical'] as $slug) {
            $entry = MuseumEntry::where('slug', $slug)->firstOrFail();
            $this->assertSame('page', $entry->type);
            $this->assertSame('draft', $entry->status);
            $this->assertNull($entry->published_at);
            $this->assertSame($slug, $entry->section->slug);
            $this->assertStringContainsString('Источник: https://muzei-xleb.ru/', $entry->excerpt);
            $this->assertSame(0, $entry->media()->count());
            $this->assertGreaterThan(100, mb_strlen((string) $entry->body));
        }
        $overview = MuseumEntry::where('slug','excursion-overview')->firstOrFail();
        $this->assertStringContainsString('космонавтов', $overview->body);
        $overview->update(['body'=>'<p>Новая версия редактора музея.</p>']);
        $this->assertSame(0, Artisan::call('museum:import-official-excursions', [
            '--apply'=>true,
        ]));
        $this->assertDatabaseCount('museum_entries', 4);
        $this->assertSame('<p>Новая версия редактора музея.</p>', $overview->fresh()->body);
    }

    public function test_children_pages_reuse_only_verified_source_sections_and_remain_drafts(): void
    {
        $this->seed(ReferenceMuseumSectionsSeeder::class);
        $this->assertSame(0, Artisan::call('museum:import-official-excursions',[
            '--children'=>true,
        ]));
        $this->assertDatabaseCount('museum_entries',0);
        $this->assertSame(0, Artisan::call('museum:import-official-excursions',[
            '--children'=>true,'--apply'=>true,
        ]), Artisan::output());
        $this->assertDatabaseCount('museum_entries',6);
        foreach (['children-interactive','children-thematic'] as $slug) {
            $entry=MuseumEntry::where('slug',$slug)->firstOrFail();
            $this->assertSame('draft',$entry->status);
            $this->assertSame('page',$entry->type);
            $this->assertNull($entry->published_at);
            $this->assertSame('children',$entry->section->parent->slug);
            $this->assertStringContainsString('muzei-xleb.ru',$entry->body);
            $this->assertStringContainsString('Возрастные ограничения',$entry->body);
            $this->assertSame(0,$entry->media()->count());
        }
        $entry=MuseumEntry::where('slug','children-thematic')->firstOrFail();
        $entry->update(['body'=>'<p>Правка редактора.</p>']);
        $this->assertSame(0, Artisan::call('museum:import-official-excursions',[
            '--children'=>true,'--apply'=>true,
        ]));
        $this->assertSame('<p>Правка редактора.</p>',$entry->fresh()->body);
        $this->assertDatabaseCount('museum_entries',6);
    }

    public function test_rejects_changed_source_html_digest_and_does_not_create_partial_import(): void
    {
        $this->seed(ReferenceMuseumSectionsSeeder::class);
        $source = json_decode((string) file_get_contents(base_path('../web/src/data/official-excursion-pages.json')),true);
        $source['pages'][2]['html']='<p>Вымышленная программа экскурсии.</p>';
        $path=storage_path('framework/testing/forged-excursion-source.json');
        if (!is_dir(dirname($path))) mkdir(dirname($path),0700,true);
        file_put_contents($path,json_encode($source,JSON_UNESCAPED_UNICODE));
        try {
            $this->assertSame(1, Artisan::call('museum:import-official-excursions', [
                '--source'=>$path,'--apply'=>true,
            ]));
            $this->assertDatabaseCount('museum_entries', 0);
        } finally {
            @unlink($path);
        }
    }

    public function test_existing_unrelated_editor_owned_slug_is_never_overwritten(): void
    {
        $this->seed(ReferenceMuseumSectionsSeeder::class);
        MuseumEntry::create([
            'slug'=>'excursion-overview','title'=>'Другая запись','type'=>'news',
            'body'=>'<p>Своя публикация.</p>','status'=>'draft',
        ]);
        $this->assertSame(1, Artisan::call('museum:import-official-excursions', [
            '--apply'=>true,
        ]));
        $this->assertDatabaseCount('museum_entries',1);
        $this->assertSame('Другая запись',MuseumEntry::firstOrFail()->title);
    }

    public function test_import_denied_in_production_without_accessing_cms(): void
    {
        $previous=app()->environment();
        app()->instance('env','production');
        try {
            $this->assertSame(1,Artisan::call('museum:import-official-excursions',[
                '--apply'=>true,
            ]));
            $this->assertDatabaseCount('museum_entries',0);
        } finally {
            app()->instance('env',$previous);
        }
    }
}
