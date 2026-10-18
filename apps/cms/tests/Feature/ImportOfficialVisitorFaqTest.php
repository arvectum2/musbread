<?php

declare(strict_types=1);

namespace Tests\Feature;

use App\Models\MuseumEntry;
use Database\Seeders\ReferenceMuseumSectionsSeeder;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Artisan;
use Tests\TestCase;

final class ImportOfficialVisitorFaqTest extends TestCase
{
    use RefreshDatabase;

    public function test_nine_verified_answers_import_as_one_private_editable_draft(): void
    {
        $this->seed(ReferenceMuseumSectionsSeeder::class);
        $this->assertSame(0, Artisan::call('museum:import-official-visitor-faq'));
        $this->assertDatabaseCount('museum_entries', 0);
        $this->assertSame(0, Artisan::call('museum:import-official-visitor-faq', [
            '--apply' => true,
        ]), Artisan::output());
        $this->assertDatabaseCount('museum_entries', 1);
        $faq = MuseumEntry::where('slug', 'faq')->firstOrFail();
        $this->assertSame('draft', $faq->status);
        $this->assertNull($faq->published_at);
        $this->assertSame('page', $faq->type);
        $this->assertSame('faq', $faq->section->slug);
        $this->assertSame(9, substr_count($faq->body, '<h2>'));
        $this->assertSame(9, substr_count($faq->body, 'Официальный музейный первоисточник'));
        $this->assertStringContainsString('съёмка', $faq->body);
        $faq->update(['body' => '<p>Изменено редактором музея.</p>']);
        $this->assertSame(0, Artisan::call('museum:import-official-visitor-faq', [
            '--apply' => true,
        ]));
        $this->assertDatabaseCount('museum_entries', 1);
        $this->assertSame('<p>Изменено редактором музея.</p>', $faq->fresh()->body);
    }

    public function test_forged_source_text_is_rejected_without_touching_cms(): void
    {
        $this->seed(ReferenceMuseumSectionsSeeder::class);
        $faqPath = base_path('../web/src/data/official-visitor-faq.json');
        $data = json_decode((string) file_get_contents($faqPath), true);
        $data['questions'][0]['source_phrases'][] = 'Вымышленное право трогать музейные экспонаты';
        $path = storage_path('framework/testing/forged-faq.json');
        if (! is_dir(dirname($path))) mkdir(dirname($path), 0700, true);
        file_put_contents($path, json_encode($data, JSON_UNESCAPED_UNICODE));
        try {
            $this->assertSame(1, Artisan::call('museum:import-official-visitor-faq', [
                '--source' => $path,
                '--apply' => true,
            ]));
            $this->assertDatabaseCount('museum_entries', 0);
        } finally {
            @unlink($path);
        }
    }

    public function test_production_bulk_import_is_refused(): void
    {
        $previous = app()->environment();
        app()->instance('env', 'production');
        try {
            $this->assertSame(1, Artisan::call('museum:import-official-visitor-faq', [
                '--apply' => true,
            ]));
            $this->assertDatabaseCount('museum_entries', 0);
        } finally {
            app()->instance('env', $previous);
        }
    }

    public function test_cannot_replace_unrelated_existing_editorial_slug(): void
    {
        $this->seed(ReferenceMuseumSectionsSeeder::class);
        MuseumEntry::create([
            'slug'=>'faq', 'type'=>'news', 'title'=>'Не FAQ', 'status'=>'draft',
            'body'=>'<p>Другая публикация.</p>',
        ]);
        $this->assertSame(1, Artisan::call('museum:import-official-visitor-faq', [
            '--apply' => true,
        ]));
        $this->assertSame('Не FAQ', MuseumEntry::where('slug', 'faq')->first()->title);
    }
}
