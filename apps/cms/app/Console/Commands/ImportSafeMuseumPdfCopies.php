<?php

namespace App\Console\Commands;

use App\Models\MuseumDocument;
use App\Models\MuseumEntry;
use App\Support\MuseumDocumentInspector;
use Illuminate\Console\Command;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Storage;
use RuntimeException;
use Throwable;

/**
 * Opt-in local materialization of PDF raster derivatives rejected by the
 * unchanged PDF inspector because of incidental /JS bytes in JPEG streams.
 * Every source and derivative must match the independent private archive.
 * This command NEVER exports to the site or marks anything accessible.
 */
final class ImportSafeMuseumPdfCopies extends Command
{
    protected $signature = 'museum:import-safe-pdf-copies
        {--apply : Write verified PDF derivatives to private draft CMS records}
        {--manifest= : Existing private SHA256 derivative manifest}';

    protected $description = 'Inspect then attach verified local museum PDF copies to source-backed drafts';

    private const APPROVED_ORIGINALS = [
        'ccaf820e83d229fa8d021d2381f648b5f8e90d6052acce6eb62c3892d8567064' => 'museum-finance',
        'ef6be6b96f4aa1da0ccdb62fbb6da32fd03411a126487f64a9d8cb679fdc0332' => 'museum-finance',
        '2e206de396dc3d404ec386dd4712efab46705d4afe9aad30bcd6625401d34c60' => 'museum-anti-corruption',
    ];

    public function handle(MuseumDocumentInspector $inspector): int
    {
        if ($this->option('apply') && app()->environment('production')) {
            $this->error('Mass source import is forbidden in production.');
            return self::FAILURE;
        }
        $root = realpath(base_path('../../.local_archive/pdf-compression'));
        $archiveRoot = realpath(base_path('../../.local_archive/official-site-originals'));
        if (! $root || ! $archiveRoot) {
            $this->error('Private verified Mac archive not mounted.');
            return self::FAILURE;
        }

        try {
            $path = $this->option('manifest') ?: $root.'/verified-derivatives.json';
            $actualManifest = realpath($path);
            if (! $actualManifest || ! str_starts_with($actualManifest, $root.'/')) {
                throw new RuntimeException('Manifest is not in protected PDF derivative archive');
            }
            $data = json_decode((string) file_get_contents($actualManifest), true, flags: JSON_THROW_ON_ERROR);
            if (($data['source'] ?? null) !== 'https://muzei-xleb.ru'
                || ($data['type'] ?? null) !== 'UNREVIEWED_RASTERIZED_PDF_DERIVATIVES'
                || ! is_array($data['copies'] ?? null) || count($data['copies']) !== 3) {
                throw new RuntimeException('Invalid trusted source and three-derivative manifest');
            }
            $originals = json_decode((string) file_get_contents($archiveRoot.'/manifest.json'),
                true, flags: JSON_THROW_ON_ERROR);
            if (($originals['source'] ?? null) !== 'https://muzei-xleb.ru'
                || ! is_array($originals['files'] ?? null)) {
                throw new RuntimeException('Original museum SHA256 inventory unavailable');
            }
            $byHash = [];
            foreach ($originals['files'] as $item) {
                $byHash[$item['sha256']] = $item;
            }
            $pending = [];
            foreach ($data['copies'] as $copy) {
                $sha = $copy['source_sha256'] ?? '';
                $ownerSlug = self::APPROVED_ORIGINALS[$sha] ?? null;
                if (! $ownerSlug || isset($pending[$sha])
                    || ($copy['target_cms_slug'] ?? null) !== $ownerSlug
                    || ($copy['accessibility_reviewed'] ?? true) !== false) {
                    throw new RuntimeException('Untrusted source ID/owner or duplicate derived PDF');
                }
                $origin = $byHash[$sha] ?? null;
                if (! $origin || ($copy['source_url'] ?? null) !== $origin['url']
                    || ($copy['source_page'] ?? null) !== $origin['source']
                    || ($copy['source_size_bytes'] ?? null) !== $origin['size_bytes']
                    || ($copy['source_label'] ?? null) !== $origin['label']
                    || ! str_starts_with($origin['url'], 'https://muzei-xleb.ru/sites/default/files/')) {
                    throw new RuntimeException('Source differs from museum original SHA256 manifest');
                }
                $sourceLocal = realpath($archiveRoot.'/'.$origin['local_name']);
                if (! $sourceLocal || ! str_starts_with($sourceLocal, $archiveRoot.'/')
                    || hash_file('sha256', $sourceLocal) !== $sha
                    || filesize($sourceLocal) !== $origin['size_bytes']) {
                    throw new RuntimeException('Official original missing/changed: '.$sha);
                }
                $name = $copy['derived_file'] ?? '';
                if (! is_string($name) || ! preg_match('/^safe_museum_[a-z0-9_]+\.pdf$/D', $name)) {
                    throw new RuntimeException('Unexpected reconstructed PDF name');
                }
                $derived = realpath($root.'/'.$name);
                if (! $derived || ! str_starts_with($derived, $root.'/')
                    || ! preg_match('/^[0-9a-f]{64}$/D', (string) ($copy['derived_sha256'] ?? ''))
                    || hash_file('sha256', $derived) !== $copy['derived_sha256']
                    || filesize($derived) !== ($copy['derived_size_bytes'] ?? null)) {
                    throw new RuntimeException('Derived PDF was modified or moved');
                }
                $inspector->verify($derived, 'pdf'); // never bypass
                $entry = MuseumEntry::where('slug', $ownerSlug)->first();
                if (! $entry || $entry->type !== 'page' || $entry->status !== 'draft'
                    || $entry->published_at !== null
                    || ! str_starts_with((string) $entry->excerpt,
                        'Источник: https://muzei-xleb.ru'.$origin['source'].';')) {
                    throw new RuntimeException('Source-backed editorial draft not found: '.$ownerSlug);
                }
                $existing = MuseumDocument::where('sha256', $copy['derived_sha256'])->first();
                if ($existing && ($existing->museum_entry_id !== $entry->id
                    || $existing->source_type !== 'pdf-recompressed')) {
                    throw new RuntimeException('Existing document digest belongs to another editor/section');
                }
                $pending[$sha] = compact('copy', 'entry', 'derived', 'existing', 'origin');
            }
            if (count($pending) !== count(self::APPROVED_ORIGINALS)) {
                throw new RuntimeException('Missing original PDF in private verified manifest');
            }
            foreach ($pending as $one) {
                $this->line(($one['existing'] ? 'KEEP' : 'NEW PRIVATE DERIVATIVE')
                    .' '.$one['entry']->slug.' '.$one['origin']['label']);
            }
            if (! $this->option('apply')) {
                $this->info('Dry run: original documents, CMS and private files untouched.');
                return self::SUCCESS;
            }
            $written = [];
            try {
                DB::transaction(function () use ($pending, &$written): void {
                    foreach ($pending as $one) {
                        if ($one['existing']) continue;
                        $copy = $one['copy'];
                        $digest = $copy['derived_sha256'];
                        $storagePath = 'museum/documents/official-source/'.$digest.'.pdf';
                        if (Storage::disk('local')->exists($storagePath)) {
                            throw new RuntimeException('Unexpected existing private file before attach');
                        }
                        if (! Storage::disk('local')->put($storagePath, file_get_contents($one['derived']))) {
                            throw new RuntimeException('Failed to store private PDF derivative');
                        }
                        $written[] = $storagePath;
                        MuseumDocument::create([
                            'museum_entry_id' => $one['entry']->id,
                            'label' => $one['origin']['label'].' (технически пересобранная копия)',
                            'file_type' => 'pdf',
                            'storage_path' => $storagePath,
                            'sha256' => $digest,
                            'size_bytes' => $copy['derived_size_bytes'],
                            'source_type' => 'pdf-recompressed',
                            'accessibility_reviewed' => false,
                            'accessibility_note' =>
                                'НЕ УТВЕРЖДЕНО КАК ДОСТУПНАЯ ВЕРСИЯ. Исходный официальный PDF: '
                                .$one['origin']['url'].'; оригинал SHA-256 '
                                .$copy['source_sha256'].'. Производная копия восстановлена из изображений; '
                                .'текстовый слой не гарантирован, OCR требует проверки редактора.',
                        ]);
                    }
                });
            } catch (Throwable $error) {
                foreach ($written as $file) Storage::disk('local')->delete($file);
                throw $error;
            }
            $this->info('Private derivatives imported; original files unchanged. No publication or accessibility approval.');
            return self::SUCCESS;
        } catch (Throwable $error) {
            $this->error('Safe import refused: '.$error->getMessage());
            return self::FAILURE;
        }
    }
}
