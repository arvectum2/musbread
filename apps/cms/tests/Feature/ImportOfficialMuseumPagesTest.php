<?php

declare(strict_types=1);

namespace Tests\Feature;

use App\Models\MuseumDocument;
use App\Models\MuseumEntry;
use App\Models\MuseumSection;
use App\Support\MuseumHtmlSanitizer;
use Database\Seeders\ReferenceMuseumSectionsSeeder;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Artisan;
use Illuminate\Support\Facades\Storage;
use Tests\TestCase;

final class ImportOfficialMuseumPagesTest extends TestCase
{
    use RefreshDatabase;

    private function importOptions(array $overrides = []): array
    {
        return array_merge([
            '--source' => base_path('../web/src/data/official-page-snapshots.json'),
        ], $overrides);
    }

    public function test_default_preview_has_no_side_effects_even_with_seeded_sections(): void
    {
        $this->seed(ReferenceMuseumSectionsSeeder::class);
        $this->assertSame(0, Artisan::call('museum:import-official-pages', $this->importOptions()));
        $this->assertStringContainsString('Dry run', Artisan::output());
        $this->assertDatabaseCount('museum_entries', 0);
        $this->assertDatabaseCount('museum_documents', 0);
        $this->assertFalse(Storage::disk('local')->exists('museum/documents/official-source/dummy.pdf'));
    }

    public function test_apply_imports_eight_private_pages_with_source_prices_links_and_keeps_editor_edits(): void
    {
        $this->seed(ReferenceMuseumSectionsSeeder::class);
        Storage::fake('local');
        $this->assertSame(0, Artisan::call('museum:import-official-pages', $this->importOptions(['--apply' => true])));
        $this->assertDatabaseCount('museum_entries', 8);
        foreach (MuseumEntry::all() as $entry) {
            $this->assertSame('draft', $entry->status);
            $this->assertNull($entry->published_at);
            $this->assertSame('page', $entry->type);
            $this->assertNotNull($entry->museum_section_id);
            $this->assertStringContainsString('https://muzei-xleb.ru/', $entry->excerpt);
            $this->assertNotEmpty(strip_tags($entry->body));
        }
        $prices = MuseumEntry::where('slug', 'tickets-and-benefits')->firstOrFail();
        $this->assertStringContainsString('<table', $prices->body);
        $this->assertStringContainsString('400 рублей', $prices->body);
        $privacy = MuseumEntry::where('slug', 'museum-privacy')->firstOrFail();
        $this->assertStringContainsString('20260203104919-1.pdf', $privacy->body);
        $this->assertStringContainsString('20260203104920-1.pdf', $privacy->body);
        $rooms = MuseumEntry::where('slug', 'museum-exposition')->firstOrFail();
        $this->assertStringContainsString('Зал «Хлеб в мировой истории»', $rooms->body);
        $this->assertStringContainsString('https://muzei-xleb.ru/ekspozicii/', $rooms->body);
        $history = MuseumEntry::where('slug', 'museum-history')->firstOrFail();
        $history->update(['body' => '<p>Редактор заменил текст!</p>', 'title' => 'Версия музея']);
        $this->assertSame(0, Artisan::call('museum:import-official-pages', $this->importOptions(['--apply' => true])));
        $this->assertSame(8, MuseumEntry::count());
        $this->assertSame('Версия музея', $history->fresh()->title);
        $this->assertSame('<p>Редактор заменил текст!</p>', trim($history->fresh()->body));
        $this->assertDatabaseCount('museum_documents', 0);
    }

    public function test_missing_required_sections_or_bad_source_hash_blocks_apply(): void
    {
        Storage::fake('local');
        $this->assertSame(1, Artisan::call('museum:import-official-pages', $this->importOptions(['--apply' => true])));
        $this->assertDatabaseCount('museum_entries', 0);
        $this->seed(ReferenceMuseumSectionsSeeder::class);
        $source = json_decode(file_get_contents(base_path('../web/src/data/official-page-snapshots.json')), true);
        $page = array_search('/stoimost', array_column($source['pages'], 'path'), true);
        $source['pages'][$page]['html'] = '<p>Текст подменён без новой подписи.</p>';
        $temp = storage_path('framework/testing/tampered-official-source.json');
        if (! is_dir(dirname($temp))) mkdir(dirname($temp), 0755, true);
        file_put_contents($temp, json_encode($source));
        try {
            $this->assertSame(1, Artisan::call('museum:import-official-pages',
                $this->importOptions(['--apply' => true, '--source' => $temp])));
            $this->assertDatabaseCount('museum_entries', 0);
        } finally {
            @unlink($temp);
        }
    }

    public function test_private_document_import_validates_checksum_skips_oversize_and_is_idempotent(): void
    {
        Storage::fake('local');
        $this->seed(ReferenceMuseumSectionsSeeder::class);
        $source = json_decode(file_get_contents(base_path('../web/src/data/official-page-snapshots.json')), true);
        $item = collect($source['pages'])->firstWhere('path', '/politika-konfidencialnosti-i-obrabotki-personalnyh-dannyh');
        $urls = array_column($item['document_links'], 'url');
        $original = "%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n<<>>\n%%EOF\n";
        $sha = hash('sha256', $original);
        $dir = storage_path('framework/testing/official-import-documents');
        if (! is_dir($dir)) mkdir($dir, 0700, true);
        file_put_contents($dir.'/'.$sha.'.pdf', $original);
        $manifest = [
            'source' => 'https://muzei-xleb.ru',
            'files' => [
                [
                    'source' => $item['path'], 'url' => $urls[0],
                    'local_name' => $sha.'.pdf', 'sha256' => $sha,
                    'size_bytes' => strlen($original),
                    'label' => 'Тестовая безопасная копия для приватного импорта',
                ],
                [
                    'source' => $item['path'], 'url' => $urls[1],
                    'local_name' => str_repeat('a', 64).'.pdf',
                    'sha256' => str_repeat('a', 64),
                    'size_bytes' => 21_000_000,
                    'label' => 'Слишком большой оригинал',
                ],
            ],
        ];
        file_put_contents($dir.'/manifest.json', json_encode($manifest));
        try {
            $this->assertSame(0, Artisan::call('museum:import-official-pages', $this->importOptions([
                '--apply' => true, '--documents' => true, '--archive' => $dir.'/manifest.json',
            ])), Artisan::output());
            $this->assertDatabaseCount('museum_documents', 1);
            // Exactly one safe original was attached; the 21 MB document
            // was not imported despite having an official URL.
            $document = MuseumDocument::firstOrFail();
            $this->assertSame($sha, $document->sha256);
            $this->assertFalse($document->accessibility_reviewed);
            $this->assertTrue(Storage::disk('local')->exists($document->storage_path));
            $this->assertSame(0, Artisan::call('museum:import-official-pages', $this->importOptions([
                '--apply' => true, '--documents' => true, '--archive' => $dir.'/manifest.json',
            ])));
            $this->assertDatabaseCount('museum_documents', 1);
            $this->assertDatabaseCount('museum_entries', 8);
        } finally {
            @unlink($dir.'/'.$sha.'.pdf');
            @unlink($dir.'/manifest.json');
            @rmdir($dir);
        }
    }

    public function test_eight_imported_drafts_do_not_leak_into_public_snapshot_until_editor_publishes(): void
    {
        $this->seed(ReferenceMuseumSectionsSeeder::class);
        Storage::fake('local');
        $this->assertSame(0, Artisan::call('museum:import-official-pages', $this->importOptions(['--apply' => true])));
        $output = storage_path('framework/testing/imported-source-public.json');
        $manifest = storage_path('framework/testing/imported-source-manifest.json');
        $media = storage_path('framework/testing/imported-source-media');
        $docs = storage_path('framework/testing/imported-source-docs');
        $options = [
            '--output' => $output, '--manifest' => $manifest,
            '--media-output-dir' => $media, '--document-output-dir' => $docs,
            '--preflight-strict' => true,
        ];
        try {
            $this->assertSame(0, Artisan::call('museum:export', $options), Artisan::output());
            $before = json_decode(file_get_contents($output), true);
            $this->assertSame([], $before['entries']);
            $entry = MuseumEntry::where('slug', 'tickets-and-benefits')->firstOrFail();
            // Publishing here is an isolated QA action, never a migration side effect.
            $entry->update(['status' => 'published', 'published_at' => now()->subMinute()]);
            $this->assertSame(0, Artisan::call('museum:export', $options), Artisan::output());
            $after = json_decode(file_get_contents($output), true);
            $this->assertCount(1, $after['entries']);
            $this->assertSame('tickets-and-benefits', $after['entries'][0]['slug']);
            $this->assertStringContainsString('400 рублей', $after['entries'][0]['body']);
            $this->assertStringContainsString('<table', $after['entries'][0]['body']);
            $this->assertSame(7, MuseumEntry::query()->where('status', 'draft')->count());
        } finally {
            @unlink($output);
            @unlink($manifest);
        }
    }

    public function test_production_mode_does_not_allow_bulk_reference_import(): void
    {
        $this->seed(ReferenceMuseumSectionsSeeder::class);
        $previous = app()->environment();
        app()->instance('env', 'production');
        try {
            $this->assertSame(1, Artisan::call('museum:import-official-pages',
                $this->importOptions(['--apply' => true])));
            $this->assertDatabaseCount('museum_entries', 0);
        } finally {
            app()->instance('env', $previous);
        }
    }

    public function test_tampered_private_manifest_rejected_before_any_database_mutation(): void
    {
        $this->seed(ReferenceMuseumSectionsSeeder::class);
        $dir = storage_path('framework/testing/official-import-invalid');
        if (! is_dir($dir)) mkdir($dir, 0700, true);
        file_put_contents($dir.'/manifest.json', json_encode([
            'source' => 'https://muzei-xleb.ru',
            'files' => [[
                'source' => '/oficialnye-dokumenty-muzeya',
                'url' => 'https://evil.example/not-on-museum-site.pdf',
                'local_name' => str_repeat('a',64).'.pdf',
                'sha256' => str_repeat('a',64),
                'size_bytes' => 200,
                'label' => 'Unverified document',
            ]],
        ]));
        try {
            $this->assertSame(1, Artisan::call('museum:import-official-pages', $this->importOptions([
                '--apply' => true, '--documents' => true, '--archive' => $dir.'/manifest.json',
            ])));
            $this->assertDatabaseCount('museum_entries', 0);
            $this->assertDatabaseCount('museum_documents', 0);
        } finally {
            @unlink($dir.'/manifest.json');
            @rmdir($dir);
        }
    }

    public function test_sanitizer_preserves_prices_table_but_strips_script_events_and_nested_unsafe_elements(): void
    {
        $safe = app(MuseumHtmlSanitizer::class)->clean(
            '<table><tbody><tr><td onclick="evil()">400 рублей</td>'
            .'<td><a href="javascript:alert(1)">Ссылка</a></td></tr></tbody></table>'
            .'<script>alert(1)</script>'
        );
        $this->assertStringContainsString('<table', $safe);
        $this->assertStringContainsString('<td>400 рублей</td>', $safe);
        $this->assertStringNotContainsString('onclick', $safe);
        $this->assertStringNotContainsString('javascript:', $safe);
        $this->assertStringNotContainsString('<script', $safe);
    }
}
