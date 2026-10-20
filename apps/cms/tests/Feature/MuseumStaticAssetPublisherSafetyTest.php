<?php

namespace Tests\Feature;

use App\Support\MuseumStaticAssetPublisher;
use Illuminate\Support\Facades\File;
use Tests\TestCase;

class MuseumStaticAssetPublisherSafetyTest extends TestCase
{
    public function test_withdrawal_removes_only_unapproved_sha_named_assets(): void
    {
        $root = storage_path('framework/testing/asset-publisher-safety');
        $mediaDir = $root.'/media';
        $documentDir = $root.'/documents';
        File::deleteDirectory($root);
        File::ensureDirectoryExists($mediaDir);
        File::ensureDirectoryExists($documentDir);

        $keepWebp = str_repeat('a', 64).'.webp';
        $withdrawnWebp = str_repeat('b', 64).'.webp';
        $keepPdf = str_repeat('c', 64).'.pdf';
        $withdrawnDocx = str_repeat('d', 64).'.docx';
        $unexpectedFiles = ['favicon.webp','operator-note.webp','foo.pdf','private.txt'];

        try {
            foreach ([$keepWebp, $withdrawnWebp, ...array_slice($unexpectedFiles, 0, 2)] as $name) {
                file_put_contents($mediaDir.'/'.$name, 'fixture');
            }
            foreach ([$keepPdf, $withdrawnDocx, ...array_slice($unexpectedFiles, 2)] as $name) {
                file_put_contents($documentDir.'/'.$name, 'fixture');
            }
            app(MuseumStaticAssetPublisher::class)->pruneWithdrawn(
                $mediaDir, $documentDir,
                ['media/'.$keepWebp => ['sha256' => str_repeat('a', 64), 'bytes' => 7]],
                ['documents/'.$keepPdf => ['sha256' => str_repeat('c', 64), 'bytes' => 7]]
            );
            $this->assertFileExists($mediaDir.'/'.$keepWebp);
            $this->assertFileDoesNotExist($mediaDir.'/'.$withdrawnWebp);
            $this->assertFileExists($documentDir.'/'.$keepPdf);
            $this->assertFileDoesNotExist($documentDir.'/'.$withdrawnDocx);
            foreach (array_slice($unexpectedFiles, 0, 2) as $name) {
                $this->assertFileExists($mediaDir.'/'.$name, 'Non-exported files must not be deleted');
            }
            foreach (array_slice($unexpectedFiles, 2) as $name) {
                $this->assertFileExists($documentDir.'/'.$name, 'Non-exported files must not be deleted');
            }
        } finally {
            File::deleteDirectory($root);
        }
    }

    public function test_missing_export_directories_can_be_pruned_without_creation(): void
    {
        $folder = storage_path('framework/testing/nonexistent-publisher-destination');
        File::deleteDirectory($folder);
        app(MuseumStaticAssetPublisher::class)->pruneWithdrawn($folder.'/media', $folder.'/documents', [], []);
        $this->assertDirectoryDoesNotExist($folder);
    }
}
