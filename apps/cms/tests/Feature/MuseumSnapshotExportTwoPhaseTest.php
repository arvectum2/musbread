<?php

namespace Tests\Feature;

use App\Models\MuseumEntry;
use App\Models\MuseumMedia;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Artisan;
use Illuminate\Support\Facades\File;
use Illuminate\Support\Facades\Storage;
use Tests\TestCase;

class MuseumSnapshotExportTwoPhaseTest extends TestCase
{
    use RefreshDatabase;

    public function test_late_bad_media_cannot_leave_partial_approved_assets_or_change_previous_export(): void
    {
        Storage::fake('local');
        $root = storage_path('framework/testing/late-bad-media-'.bin2hex(random_bytes(7)));
        File::ensureDirectoryExists($root.'/media');
        File::ensureDirectoryExists($root.'/documents');
        $out = $root.'/published.json';
        $manifest = $root.'/manifest.json';
        file_put_contents($out, 'previous-published-version');
        file_put_contents($manifest, 'previous-signed-manifest');

        $entry = MuseumEntry::create([
            'type' => 'news', 'slug' => 'two-phase-late-media',
            'title' => 'Подтверждённая статья', 'body' => '<p>Текст музея</p>',
            'status' => 'published',
        ]);
        $image = imagecreatetruecolor(8, 8);
        imagefilledrectangle($image, 0, 0, 7, 7, imagecolorallocate($image, 45, 70, 95));
        ob_start();
        imagewebp($image, null, 85);
        $bytes = ob_get_clean();
        imagedestroy($image);
        $sha = hash('sha256', $bytes);
        Storage::disk('local')->put('museum/media/first.webp', $bytes);

        MuseumMedia::create([
            'museum_entry_id' => $entry->id,
            'storage_path' => 'museum/media/first.webp',
            'sha256' => $sha, 'alt' => 'Экспонат в музейном зале с подписью',
            'width' => 8, 'height' => 8, 'size_bytes' => strlen($bytes),
            'source_rights_pending' => false,
        ]);
        MuseumMedia::create([
            'museum_entry_id' => $entry->id,
            'storage_path' => 'museum/media/missing.webp',
            'sha256' => str_repeat('b', 64), 'alt' => 'Второй экспонат возле стеллажа',
            'width' => 8, 'height' => 8, 'size_bytes' => 51,
            'source_rights_pending' => false,
        ]);

        $privateStages = storage_path('app/private/museum-export-stages/stage-*');
        $beforeStages = glob($privateStages) ?: [];
        try {
            $this->assertSame(0 !== Artisan::call('museum:export', [
                '--output' => $out, '--manifest' => $manifest,
                '--media-output-dir' => $root.'/media',
                '--document-output-dir' => $root.'/documents',
            ]), true, 'Invalid second asset must abort export');
        } catch (\RuntimeException $e) {
            $this->assertStringContainsString('Uploaded image checksum', $e->getMessage());
        } finally {
            $this->assertSame('previous-published-version', file_get_contents($out));
            $this->assertSame('previous-signed-manifest', file_get_contents($manifest));
            $this->assertFileDoesNotExist($root.'/media/'.$sha.'.webp',
                'The first valid image must not leak when a later image fails');
            $this->assertSame([], glob($root.'/media/*'));
            $this->assertSame([], glob($root.'/documents/*'));
            $this->assertSame($beforeStages, glob($privateStages) ?: [],
                'Failed export must also remove its private staging folder');
            File::deleteDirectory($root);
        }
    }
}
