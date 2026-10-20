<?php

namespace Tests\Feature;

use App\Models\MuseumDocument;
use App\Models\MuseumEntry;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Storage;
use Illuminate\Support\Facades\File;
use MoonShine\Laravel\Models\MoonshineUser;
use Tests\TestCase;

/** Each PHPUnit process is a real authenticated Laravel request in its own DB.
 * Python starts concurrent isolated workers; never reuse museum originals.
 */
final class MuseumDocumentLoadTest extends TestCase
{
    use RefreshDatabase;

    public function test_private_large_pdf_read_is_bounded_and_byte_identical(): void
    {
        $sizeMiB = (int) (getenv('MUSBREAD_LOAD_DOC_MIB') ?: 1);
        $this->assertContains($sizeMiB, [1, 8, 14]);
        // Each parallel PHPUnit process must have its own on-SSD root:
        // Storage::fake('local') deletes one GLOBAL shared testing path.
        $privateRoot = storage_path('framework/testing/load-private-'
            .getmypid().'-'.bin2hex(random_bytes(6)));
        File::ensureDirectoryExists($privateRoot);
        config(['filesystems.disks.local.root' => $privateRoot]);
        Storage::forgetDisk('local');
        try {
        $prefix = "%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n";
        $suffix = "\ntrailer\n<<>>\n%%EOF\n";
        $bytes = $sizeMiB * 1024 * 1024;
        $pdf = $prefix.str_repeat(' ', $bytes - strlen($prefix) - strlen($suffix)).$suffix;
        $sha = hash('sha256', $pdf);
        $entry = MuseumEntry::create([
            'type' => 'document',
            'slug' => 'synthetic-private-load-'.bin2hex(random_bytes(5)),
            'title' => 'Синтетический файл',
            'body' => '<p>Только локальное нагрузочное испытание.</p>',
            'status' => 'draft',
        ]);
        $path = 'museum/documents/synthetic-bounded-load.pdf';
        Storage::disk('local')->put($path, $pdf);
        $document = MuseumDocument::create([
            'museum_entry_id' => $entry->id,
            'label' => 'Тестовый документ',
            'file_type' => 'pdf',
            'storage_path' => $path,
            'sha256' => $sha,
            'size_bytes' => $bytes,
        ]);
        unset($pdf);
        gc_collect_cycles();
        $this->actingAs(MoonshineUser::factory()->create(), 'moonshine');
        $start = hrtime(true);
        $response = $this->get(route('museum.documents.download', $document));
        $elapsed = (hrtime(true) - $start) / 1e6;
        $response->assertOk()->assertHeader('Content-Type', 'application/octet-stream');
        $this->assertSame($bytes, strlen($response->getContent()));
        $this->assertSame($sha, hash('sha256', $response->getContent()));
        $this->assertSame([], glob(storage_path('framework/museum-check-*')) ?: []);

        $observed = [
            'document_mib' => $sizeMiB,
            'elapsed_ms' => round($elapsed, 2),
            'peak_php_mib' => round(memory_get_peak_usage(true) / 1048576, 2),
            'real_private_route' => true,
            'sha256_verified' => true,
            'memory_limit' => ini_get('memory_limit'),
            'status' => 200,
        ];
        $resultFile = getenv('MUSBREAD_LOAD_OBSERVATION_PATH');
        if ($resultFile !== false) {
            $expectedDir = realpath(base_path('../../.local_archive'));
            $actualDir = realpath(dirname($resultFile));
            // APFS can preserve different path casing for the same inode.
            // Verify device+inode identity instead of case-sensitive spelling.
            $a = $expectedDir !== false ? stat($expectedDir) : false;
            $b = $actualDir !== false ? stat($actualDir) : false;
            if ($a === false || $b === false
                || $a['dev'] !== $b['dev'] || $a['ino'] !== $b['ino']
                || ! preg_match('/^cms-load-[a-f0-9]{24}\.json$/D', basename($resultFile))) {
                throw new \RuntimeException('Unsafe synthetic load observation destination');
            }
            file_put_contents($resultFile, json_encode($observed, JSON_THROW_ON_ERROR)."\n");
        }
        } finally {
            Storage::forgetDisk('local');
            File::deleteDirectory($privateRoot);
        }
    }
}
