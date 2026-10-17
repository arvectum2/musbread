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
        {--append-documents : Explicitly append missing checked originals to existing source-origin drafts}
        {--rooms : Preview or import eleven official exposition rooms as existing CMS page drafts}
        {--rooms-source= : Override the room snapshot JSON only for local testing}
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
        '/finansovo-hozyaystvennaya-deyatelnost' => 'museum-finance',
        '/protivodeystvie-korrupcii' => 'museum-anti-corruption',
        '/politika-obespecheniya-usloviy-dostupnosti-dlya-invalidov-i-drugih-mobilnyh-grazhdan' => 'museum-accessibility-policy',
    ];

    /** Exact source URL allowlist, not text matching of a changing title. */
    private const REFUND_DOCUMENT_URLS = [
        'https://muzei-xleb.ru/sites/default/files/page/20260203113223-1.pdf',
        'https://muzei-xleb.ru/sites/default/files/page/20260203113346-prilozhenie_1_k_polozheniyu_o_vozvrate.docx',
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
        if ($this->option('append-documents') && (! $this->option('documents') || ! $this->option('apply'))) {
            $this->error('Append mode requires explicit --apply --documents --append-documents.');
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
            $rooms = $this->option('rooms') ? $this->loadRooms($byPath) : [];
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

        if ($rooms) {
            if (! MuseumSection::where('slug', 'museum-exposition')->exists()) {
                $this->error('CMS exposition parent section missing');
                return self::FAILURE;
            }
            foreach ($rooms as $room) {
                $exists = MuseumEntry::where('slug', $room['slug'])->first();
                if ($exists && ($exists->type !== 'page'
                    || $exists->section?->slug !== 'museum-exposition')) {
                    $this->error('CMS room slug already belongs to another section: '.$room['slug']);
                    return self::FAILURE;
                }
                $this->line(($exists ? 'KEEP EDITOR' : 'NEW DRAFT ROOM').' '.$room['title']
                    .' ← '.$room['source_url']);
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
            DB::transaction(function () use ($plan, $archive, $rooms, $inspector, &$createdFiles,
                &$created, &$attached, &$skippedFiles): void {
                foreach ($plan as $slug => $page) {
                    // firstOrCreate is intentionally non-destructive for all editor-owned fields.
                    $displayTitle = $slug === 'ticket-refunds'
                        ? 'Порядок возврата билетов' : (string) $page['title'];
                    $displayH1 = $slug === 'ticket-refunds'
                        ? 'Возврат билетов' : (string) $page['title'];
                    $entry = MuseumEntry::query()->firstOrCreate(['slug' => $slug], [
                        'type' => 'page',
                        'title' => mb_substr($displayTitle, 0, 255),
                        'h1' => mb_substr($displayH1, 0, 255),
                        'museum_section_id' => MuseumSection::query()->where('slug', $slug)->value('id'),
                        'excerpt' => 'Источник: '.$page['source_url'].'; снимок: '.$page['captured_utc'],
                        'body' => $page['html'],
                        'status' => 'draft',
                    ]);
                    if (! $entry->wasRecentlyCreated) {
                        $this->comment('Already exists, preserving all editorial fields and files: '.$slug);
                        if (! $this->option('append-documents')) continue;
                        if ($entry->status !== 'draft'
                            || ! str_starts_with((string) $entry->excerpt, 'Источник: '.$page['source_url'].';')) {
                            throw new RuntimeException('Cannot append museum originals to an edited/published/non-source entry: '.$slug);
                        }
                    } else {
                        $created++;
                    }
                    foreach ($archive[$page['path']] ?? [] as $file) {
                        // No duplicate or relink of existing editor-owned documents;
                        // one local digest represents one immutable source file.
                        if (MuseumDocument::query()->where('sha256', $file['sha256'])->exists()) continue;
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
                            // This legacy landing page contains many unrelated files.
                            // Only the original refund regulation and its application form
                            // belong to TZ-142; other service/orders files belong in the
                            // official document hub, without inventing a new content model.
                            $fileOwner = $entry;
                            if ($page['path'] === '/ceny-i-usloviya-predostavleniya-uslug'
                                && ! in_array($file['url'], self::REFUND_DOCUMENT_URLS, true)) {
                                $fileOwner = MuseumEntry::where('slug', 'museum-documents')->firstOrFail();
                            }
                            MuseumDocument::create([
                                'museum_entry_id' => $fileOwner->id,
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
                if ($rooms) {
                    $sectionId = MuseumSection::where('slug', 'museum-exposition')->value('id');
                    foreach ($rooms as $index => $room) {
                        // Exact CMS type/section, no image publication and no
                        // overwriting an editor's room text or publishing it.
                        $entry = MuseumEntry::firstOrCreate(['slug' => $room['slug']], [
                            'type' => 'page',
                            'title' => $room['title'],
                            'h1' => $room['title'],
                            'museum_section_id' => $sectionId,
                            'sort_order' => $index + 1,
                            'excerpt' => $room['excerpt'],
                            'body' => $room['html'].'<p><a href="'.$room['source_url'].'">'
                                .'Официальный первоисточник экспозиции</a> '
                                .'(снимок '.substr($room['captured_utc'], 0, 10).').</p>',
                            'status' => 'draft',
                        ]);
                        if ($entry->wasRecentlyCreated) $created++;
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

    /**
     * @param array<string,array<string,mixed>> $pages
     * @return list<array<string,mixed>>
     */
    private function loadRooms(array $pages): array
    {
        $path = $this->option('rooms-source')
            ?: base_path('../web/src/data/official-exposition-rooms.json');
        $data = json_decode((string) file_get_contents($path), true, flags: JSON_THROW_ON_ERROR);
        $listing = $pages['/ekspozicii']['html'] ?? '';
        if (($data['source'] ?? null) !== 'https://muzei-xleb.ru'
            || ($data['listing_source_url'] ?? null) !== 'https://muzei-xleb.ru/ekspozicii'
            || ! is_array($data['rooms'] ?? null) || count($data['rooms']) !== 11
            || ! is_string($listing) || $listing === '') {
            throw new RuntimeException('Expected eleven exposition rooms from existing official listing');
        }
        $slugs = [];
        foreach ($data['rooms'] as $room) {
            $slug = $room['slug'] ?? null;
            $url = $room['source_url'] ?? null;
            $title = $room['title'] ?? null;
            if (! is_string($slug) || ! preg_match('/^[a-z0-9]+(?:-[a-z0-9]+)*$/D', $slug)
                || isset($slugs[$slug]) || ! is_string($url)
                || ! preg_match('#^https://muzei-xleb\\.ru/ekspozicii/20\\d\\d-\\d\\d-\\d\\d/[a-z0-9-]+$#D', $url)
                || ! str_ends_with($url, '/'.$slug)
                || ! str_contains($listing, 'href="'.$url.'"')
                || ! is_string($title) || ! str_contains($listing, $title)
                || ! is_string($room['html'] ?? null) || mb_strlen($room['html']) < 90
                || ! is_string($room['excerpt'] ?? null) || trim($room['excerpt']) === ''
                || ! is_string($room['captured_utc'] ?? null)
                || ! preg_match('/^\\d{4}-\\d\\d-\\d\\dT/', $room['captured_utc'])
                || ! is_string($room['html_sha256'] ?? null)
                || hash('sha256', $room['html']) !== $room['html_sha256']
                || ($room['media_rights_confirmed'] ?? null) !== false) {
                throw new RuntimeException('Exposition room source/signature mismatch: '.(string) $slug);
            }
            $slugs[$slug] = true;
        }
        return $data['rooms'];
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
