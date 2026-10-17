<?php

declare(strict_types=1);

namespace Tests\Feature;

use App\Models\MuseumDocument;
use App\Models\MuseumEntry;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Artisan;
use Illuminate\Support\Facades\Storage;
use Tests\TestCase;

final class ImportSafeMuseumPdfCopiesTest extends TestCase
{
    use RefreshDatabase;

    private function testManifest(array $overrides): string
    {
        $dir = base_path('../../.local_archive/pdf-compression');
        if (! is_dir($dir)) mkdir($dir, 0700, true);
        $path = $dir.'/test-bad-safe-derivatives.json';
        file_put_contents($path, json_encode(array_replace([
            'source' => 'https://muzei-xleb.ru',
            'type' => 'UNREVIEWED_RASTERIZED_PDF_DERIVATIVES',
            'copies' => [],
        ], $overrides), JSON_UNESCAPED_UNICODE));
        return $path;
    }

    public function test_dry_run_refuses_incomplete_manifest_without_touching_database_or_files(): void
    {
        Storage::fake('local');
        $path = $this->testManifest(['copies' => []]);
        try {
            $this->assertSame(1, Artisan::call('museum:import-safe-pdf-copies', [
                '--manifest' => $path,
            ]));
            $this->assertDatabaseCount('museum_documents', 0);
            $this->assertDatabaseCount('museum_entries', 0);
            $this->assertFalse(Storage::disk('local')->exists('museum/documents/official-source/test.pdf'));
        } finally {
            @unlink($path);
        }
    }

    public function test_refuses_forged_source_before_any_files_or_entries_are_created(): void
    {
        Storage::fake('local');
        $path = $this->testManifest([
            'source' => 'https://example.com',
            'copies' => array_fill(0, 3, [
                'source_sha256' => str_repeat('a', 64),
                'target_cms_slug' => 'museum-finance',
                'accessibility_reviewed' => false,
            ]),
        ]);
        try {
            $this->assertSame(1, Artisan::call('museum:import-safe-pdf-copies', [
                '--apply' => true, '--manifest' => $path,
            ]));
            $this->assertDatabaseCount('museum_documents', 0);
            $this->assertDatabaseCount('museum_entries', 0);
        } finally {
            @unlink($path);
        }
    }

    public function test_production_blocks_even_valid_preview_path_on_apply(): void
    {
        $previous = app()->environment();
        app()->instance('env', 'production');
        try {
            $this->assertSame(1, Artisan::call('museum:import-safe-pdf-copies', [
                '--apply' => true,
            ]));
            $this->assertDatabaseCount('museum_documents', 0);
            $this->assertDatabaseCount('museum_entries', 0);
        } finally {
            app()->instance('env', $previous);
        }
    }

    public function test_manifest_outside_private_verified_archive_is_rejected(): void
    {
        $path = storage_path('framework/testing/foreign-safe-derivatives.json');
        if (! is_dir(dirname($path))) mkdir(dirname($path), 0700, true);
        file_put_contents($path, '{}');
        try {
            $this->assertSame(1, Artisan::call('museum:import-safe-pdf-copies', [
                '--manifest' => $path,
            ]));
            $this->assertDatabaseCount('museum_documents', 0);
        } finally {
            @unlink($path);
        }
    }
}
