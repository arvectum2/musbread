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
 * Only literal museum-owned published menu pages absent in the previous pass.
 * Never imports visitor comments, archived COVID requirements, or guessed data.
 */
final class ImportOfficialMenuGapPages extends Command
{
    protected $signature = 'museum:import-official-menu-gaps
       {--apply : Write missing source-backed legal page drafts}
       {--documents : Attach unchanged verified original PDFs to the drafts}
       {--source= : Captured original menu content JSON}
       {--archive= : Local privately cached original PDF manifest}';
    protected $description = 'Preserve real official menu sections and PDFs from existing museum without OCR';

    private const PAGE_MAP = [
        '/uchetnaya-politika' => 'museum-accounting-policy',
        '/protivodeystvie-terrorizmu' => 'museum-anti-terror',
        '/antimonopolnyy-komplaens' => 'museum-antimonopoly',
    ];

    public function handle(MuseumDocumentInspector $inspector): int
    {
        if ($this->option('apply') && app()->environment('production')) {
            $this->error('Production source bulk import is prohibited. Editorial release only.');
            return self::FAILURE;
        }
        if ($this->option('documents') && ! $this->option('apply')) {
            $this->error('--documents needs --apply.');
            return self::FAILURE;
        }
        try {
            $path = $this->option('source') ?: base_path('../web/src/data/official-museum-menu-gaps.json');
            $source = json_decode((string) file_get_contents($path), true, flags: JSON_THROW_ON_ERROR);
            if (($source['source'] ?? '') !== 'https://muzei-xleb.ru'
                || ! is_array($source['pages'] ?? null)) {
                throw new RuntimeException('Unexpected original museum menu source');
            }
            $pages = [];
            foreach ($source['pages'] as $page) {
                $url = $page['source_url'] ?? '';
                $path = $page['path'] ?? '';
                if (! is_string($path) || ! is_string($url)
                    || $url !== 'https://muzei-xleb.ru'.$path
                    || isset($pages[$path])
                    || ! is_string($page['html'] ?? null)
                    || ! is_string($page['html_sha256'] ?? null)
                    || ! hash_equals(hash('sha256', $page['html']), $page['html_sha256'])) {
                    throw new RuntimeException('Invalid museum page source hash or URL');
                }
                $pages[$path] = $page;
            }
            $sectionIds = [];
            foreach (self::PAGE_MAP as $path => $slug) {
                $page = $pages[$path] ?? null;
                if (!$page || mb_strlen((string) ($page['html'] ?? '')) < 70
                    || trim((string) ($page['title'] ?? '')) === ''
                    || ! preg_match('/^20\d\d-\d\d-\d\dT/', (string)($page['captured_utc'] ?? ''))) {
                    throw new RuntimeException('Original live museum page missing: '.$path);
                }
                $section = MuseumSection::where('slug', $slug)->first();
                if (!$section) throw new RuntimeException('Preexisting CMS section missing: '.$slug);
                $sectionIds[$slug] = $section->id;
                $existing = MuseumEntry::where('slug', $slug)->first();
                if ($existing && ($existing->type !== 'page'
                    || (int)$existing->museum_section_id !== (int)$section->id)) {
                    throw new RuntimeException('Source import would overwrite unrelated editor page: '.$slug);
                }
                $this->line(($existing ? 'KEEP EDITOR' : 'NEW PRIVATE DRAFT')
                    .' '.$slug.' ← '.$page['source_url']);
            }
            $files = [];
            if ($this->option('documents')) {
                $manifestPath = $this->option('archive')
                    ?: base_path('../../.local_archive/official-menu-originals/manifest.json');
                $manifest = json_decode((string)file_get_contents($manifestPath),true,flags:JSON_THROW_ON_ERROR);
                if (($manifest['source'] ?? '') !== 'https://muzei-xleb.ru'
                    || ! is_array($manifest['files'] ?? null)
                    || ! empty($manifest['errors'] ?? [])) {
                    throw new RuntimeException('Original PDF archive incomplete/untrusted');
                }
                foreach ($manifest['files'] as $file) {
                    $path = $file['source'] ?? '';
                    $href = $file['url'] ?? '';
                    $sha = $file['sha256'] ?? '';
                    $name = $file['local_name'] ?? '';
                    if (! isset(self::PAGE_MAP[$path])
                        || ! in_array($href,array_column($pages[$path]['document_links'] ?? [], 'url'),true)
                        || ! preg_match('#^https://muzei-xleb\.ru/sites/default/files/.+\.pdf$#D',$href)
                        || ! preg_match('/^[a-f0-9]{64}$/D',(string)$sha)
                        || $name !== $sha.'.pdf'
                        || !is_int($file['size_bytes'] ?? null)) {
                        throw new RuntimeException('Original PDF manifest does not match verified museum page');
                    }
                    $local = dirname($manifestPath).'/'.$name;
                    if (! is_file($local) || filesize($local) !== $file['size_bytes']
                        || hash_file('sha256',$local) !== $sha) {
                        throw new RuntimeException('Original cached PDF byte/hash mismatch: '.$name);
                    }
                    $files[] = [...$file, '_path'=>$local];
                }
                if (count($files) !== 11) {
                    throw new RuntimeException('Expected exactly 11 verified PDF links from three real museum legal pages');
                }
            }
            if (! $this->option('apply')) {
                $this->info('Dry run: no CMS pages or documents modified.');
                return self::SUCCESS;
            }
            $created = 0; $attached = 0; $skipped = 0; $copied = [];
            try {
                DB::transaction(function () use ($pages, $sectionIds, $files, $inspector,
                    &$created, &$attached, &$skipped, &$copied):void {
                    foreach (self::PAGE_MAP as $path=>$slug) {
                        $page = $pages[$path];
                        $entry = MuseumEntry::firstOrCreate(['slug'=>$slug], [
                            'museum_section_id'=>$sectionIds[$slug],
                            'type'=>'page',
                            'title'=>mb_substr($page['title'],0,255),
                            'h1'=>mb_substr($page['title'],0,255),
                            'excerpt'=>'Источник: '.$page['source_url'].'; снимок: '.$page['captured_utc'],
                            'body'=>$page['html'],
                            'status'=>'draft',
                        ]);
                        if ($entry->wasRecentlyCreated) $created++;
                        foreach ($files as $file) {
                            if ($file['source']!==$path) continue;
                            if (MuseumDocument::where('sha256',$file['sha256'])->exists()) {
                                $skipped++;
                                continue;
                            }
                            // Do not add documents to a previously changed or
                            // published editor-owned entry without museum action.
                            if (!$entry->wasRecentlyCreated
                                && ($entry->status!=='draft'
                                    || !str_starts_with((string)$entry->excerpt,'Источник: '.$page['source_url'].';'))) {
                                throw new RuntimeException('Edited CMS item cannot receive source PDFs: '.$slug);
                            }
                            if ($file['size_bytes']>MuseumDocumentInspector::MAX_BYTES) {
                                $this->warn('Keep large original PDF as official site href: '.$file['label']);
                                $skipped++;
                                continue;
                            }
                            try {
                                $inspector->verify($file['_path'],'pdf');
                            } catch (ValidationException $e) {
                                $this->warn('Keep checked original as external source link, no rewrite: '.$file['label']);
                                $skipped++;
                                continue;
                            }
                            $target='museum/documents/official-menu/'.$file['local_name'];
                            if (Storage::disk('local')->exists($target)) {
                                if (hash_file('sha256',Storage::disk('local')->path($target)) !== $file['sha256']) {
                                    throw new RuntimeException('Protected stored original differs');
                                }
                            } else {
                                if(!Storage::disk('local')->put($target,file_get_contents($file['_path']))) {
                                    throw new RuntimeException('Failed to preserve exact PDF bytes');
                                }
                                $copied[]=$target;
                            }
                            MuseumDocument::create([
                                'museum_entry_id'=>$entry->id,
                                'label'=>mb_substr((string)$file['label'],0,180),
                                'file_type'=>'pdf',
                                'storage_path'=>$target,
                                'sha256'=>$file['sha256'],
                                'size_bytes'=>$file['size_bytes'],
                                'source_type'=>'official-site',
                                'accessibility_reviewed'=>false,
                            ]);
                            $attached++;
                        }
                    }
                });
            } catch(Throwable $ex) {
                Storage::disk('local')->delete($copied);
                throw $ex;
            }
            $this->info("Preserved $created new private source-backed legal pages,"
                ." $attached unmodified PDF files, $skipped references already present or beyond safe upload."
                ." No publication or OCR.");
            return self::SUCCESS;
        } catch(Throwable $e) {
            $this->error('Import stopped safely: '.$e->getMessage());
            return self::FAILURE;
        }
    }
}
