<?php

declare(strict_types=1);

namespace App\Console\Commands;

use App\Models\MuseumDocument;
use App\Models\MuseumEntry;
use App\Models\MuseumSection;
use App\Support\MuseumDocumentInspector;
use Illuminate\Console\Command;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Storage;
use Illuminate\Validation\ValidationException;
use RuntimeException;
use Throwable;

/**
 * Explicit local import of previously captured public museum source editions.
 * Never fetches the network and never edits existing editorial content.
 */
final class ImportOfficialMuseumPages extends Command
{
    protected $signature = 'museum:import-official-pages
        {--apply : Write missing draft pages to the existing MoonShine database}
        {--documents : Attach validated local original documents (requires --apply)}
        {--archive= : Optional private original document manifest; default is .local_archive}
        {--source= : Optional snapshot JSON; default is the captured museum-source file}';

    protected $description = 'Preview or import official-site content into private draft CMS entries without overwriting editor work';

    /** Exact sections with matching source paths from the saved public snapshot. */
    private const PATH_TO_SLUG = [
        '/oficialnye-dokumenty-muzeya' => 'museum-documents',
        '/politika-konfidencialnosti-i-obrabotki-personalnyh-dannyh' => 'museum-privacy',
        '/stoimost' => 'tickets-and-benefits',
        '/ceny-i-usloviya-predostavleniya-uslug' => 'ticket-refunds',
        '/o-muzee' => 'museum-history',
        '/istoriya-zdaniya' => 'building-history',
        '/ekspozicii' => 'museum-exposition',
        '/vakansii' => 'museum-vacancies',
    ];

    public function handle(MuseumDocumentInspector $inspector): int
    {
        if (app()->environment('production') && $this->option('apply')) {
            $this->error('Import on production is forbidden: use reviewed CMS editorial actions.');
            return self::FAILURE;
        }
        if ($this->option('documents') && ! $this->option('apply')) {
            $this->error('Document attachment needs explicit --apply.');
            return self::FAILURE;
        }
        $path = $this->option('source') ?: base_path('../web/src/data/official-page-snapshots.json');
        try {
            $payload = json_decode((string) file_get_contents($path), true, flags: JSON_THROW_ON_ERROR);
            if (! is_array($payload) || ($payload['source'] ?? null) !== 'https://muzei-xleb.ru'
                || ! isset($payload['pages']) || ! is_array($payload['pages'])) {
                throw new RuntimeException('Unexpected official museum capture source');
            }
            $byPath = [];
            foreach ($payload['pages'] as $page) {
                if (! is_array($page) || ! isset($page['path']) || isset($byPath[$page['path']])) {
                    throw new RuntimeException('Invalid or duplicate source page');
                }
                $byPath[$page['path']] = $page;
            }
            $plan = [];
            foreach (self::PATH_TO_SLUG as $sourcePath => $slug) {
                $page = $byPath[$sourcePath] ?? null;
                if ($page === null || ($page['source_url'] ?? null) !== 'https://muzei-xleb.ru'.$sourcePath
                    || ! is_string($page['html'] ?? null) || strlen($page['html']) < 80
                    || ! is_string($page['title'] ?? null) || trim($page['title']) === ''
                    || ! preg_match('/^[0-9a-f]{64}$/D', (string) ($page['html_sha256'] ?? ''))
                    || hash('sha256', $page['html']) !== $page['html_sha256']
                    || ! is_string($page['captured_utc'] ?? null)
                    || ! preg_match('/^\d{4}-\d\d-\d\dT/', $page['captured_utc'])) {
                    throw new RuntimeException('Incomplete or modified official snapshot for '.$slug);
                }
                $plan[$slug] = $page;
            }
            $archive = $this->option('documents') ? $this->loadArchive($byPath) : [];
        } catch (Throwable $e) {
            $this->error('Reference import stopped: '.$e->getMessage());
            return self::FAILURE;
        }

        foreach ($plan as $slug => $page) {
            $exists = MuseumEntry::query()->where('slug', $slug)->exists();
            $sectionExists = MuseumSection::query()->where('slug', $slug)->exists();
            $this->line(($exists ? 'KEEP' : ($sectionExists ? 'NEW DRAFT' : 'NEEDS SECTION'))
                .' '.$slug.' ← '.$page['source_url']);
            if (! $sectionExists && ! $exists && $this->option('apply')) {
                $this->error('Missing CMS section '.$slug.'; run opt-in ReferenceMuseumSectionsSeeder first.');
                return self::FAILURE;
            }
        }

        if (! $this->option('apply')) {
            $this->info('Dry run: no DB, files, publication state, or CMS versions changed.');
            return self::SUCCESS;
        }
        $createdFiles = [];
        $created = 0;
        $attached = 0;
        $skippedFiles = 0;
        try {
            DB::transaction(function () use ($plan, $archive, $inspector, &$createdFiles,
                &$created, &$attached, &$skippedFiles): void {
                foreach ($plan as $slug => $page) {
                    // firstOrCreate is intentionally non-destructive for all editor-owned fields.
                    $entry = MuseumEntry::query()->firstOrCreate(['slug' => $slug], [
                        'type' => 'page',
                        'title' => mb_substr((string) $page['title'], 0, 255),
                        'h1' => mb_substr((string) $page['title'], 0, 255),
                        'museum_section_id' => MuseumSection::query()->where('slug', $slug)->value('id'),
                        'excerpt' => 'Источник: '.$page['source_url'].'; снимок: '.$page['captured_utc'],
                        'body' => $page['html'],
                        'status' => 'draft',
                    ]);
                    if (! $entry->wasRecentlyCreated) {
                        $this->comment('Already exists, preserving editorial data and all attached files: '.$slug);
                        continue;
                    }
                    $created++;
                    foreach ($archive[$page['path']] ?? [] as $file) {
                        $extension = pathinfo($file['local_name'], PATHINFO_EXTENSION);
                        $sourceFile = dirname($file['_manifest']).'/'.$file['local_name'];
                        try {
                            if (($file['size_bytes'] ?? 0) > MuseumDocumentInspector::MAX_BYTES) {
                                throw new RuntimeException('Exceeds existing CMS 15MiB limit');
                            }
                            if (! is_file($sourceFile) || filesize($sourceFile) !== $file['size_bytes']
                                || hash_file('sha256', $sourceFile) !== $file['sha256']) {
                                throw new RuntimeException('Original file changed or missing');
                            }
                            $inspector->verify($sourceFile, $extension);
                            $destination = 'museum/documents/official-source/'.$file['local_name'];
                            if (Storage::disk('local')->exists($destination)) {
                                if (hash_file('sha256', Storage::disk('local')->path($destination)) !== $file['sha256']) {
                                    throw new RuntimeException('Existing private document has a different digest');
                                }
                            } else {
                                if (! Storage::disk('local')->put($destination, file_get_contents($sourceFile))) {
                                    throw new RuntimeException('Cannot store original in private CMS storage');
                                }
                                $createdFiles[] = $destination;
                            }
                            MuseumDocument::create([
                                'museum_entry_id' => $entry->id,
                                'label' => mb_substr((string) $file['label'], 0, 180),
                                'file_type' => $extension,
                                'storage_path' => $destination,
                                'sha256' => $file['sha256'],
                                'size_bytes' => $file['size_bytes'],
                                'accessibility_reviewed' => false,
                            ]);
                            $attached++;
                        } catch (ValidationException|RuntimeException $error) {
                            // The exact official HTTPS anchor remains in the imported body.
                            // Do not bypass upload restrictions to make the dashboard greener.
                            $skippedFiles++;
                            $this->warn('Document kept as external official link: '.$file['label']
                                .' ('.$error->getMessage().')');
                        }
                    }
                }
            });
        } catch (Throwable $error) {
            Storage::disk('local')->delete($createdFiles);
            $this->error('Import transaction rolled back: '.$error->getMessage());
            return self::FAILURE;
        }
        $this->info("Imported $created draft pages, $attached private document attachments; "
            ."$skippedFiles documents remain as source-site links. No publication triggered.");
        return self::SUCCESS;
    }

    /** @return array<string,list<array<string,mixed>>> */
    private function loadArchive(array $pages): array
    {
        $path = $this->option('archive') ?: base_path('../../.local_archive/official-site-originals/manifest.json');
        $manifest = json_decode((string) file_get_contents($path), true, flags: JSON_THROW_ON_ERROR);
        if (($manifest['source'] ?? null) !== 'https://muzei-xleb.ru'
            || ! is_array($manifest['files'] ?? null)) {
            throw new RuntimeException('Unexpected document archive manifest');
        }
        $map = [];
        foreach ($manifest['files'] as $file) {
            $url = $file['url'] ?? null;
            $sha = $file['sha256'] ?? null;
            $fileName = $file['local_name'] ?? null;
            $source = $file['source'] ?? null;
            $ext = pathinfo((string) $fileName, PATHINFO_EXTENSION);
            if (! is_string($url) || ! str_starts_with($url, 'https://muzei-xleb.ru/sites/default/files/')
                || ! is_string($source) || ! isset($pages[$source])
                || ! in_array($url, array_column($pages[$source]['document_links'] ?? [], 'url'), true)
                || ! is_string($sha) || ! preg_match('/^[0-9a-f]{64}$/D', $sha)
                || ! in_array($ext, MuseumDocumentInspector::EXTENSIONS, true)
                || $fileName !== $sha.'.'.$ext || ! is_int($file['size_bytes'] ?? null)
                || $file['size_bytes'] < 16 || ! is_string($file['label'] ?? null)) {
                throw new RuntimeException('Invalid or inconsistent official document record');
            }
            $file['_manifest'] = $path;
            $map[$source][] = $file;
        }
        return $map;
    }
}
