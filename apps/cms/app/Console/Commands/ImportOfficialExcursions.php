<?php

namespace App\Console\Commands;

use App\Models\MuseumEntry;
use App\Models\MuseumSection;
use Illuminate\Console\Command;
use Illuminate\Support\Facades\DB;
use RuntimeException;
use Throwable;

/**
 * Four official museum excursion index pages. Only existing MoonShine page
 * model; never create fake tours/events, dates, photos, prices or sales.
 */
final class ImportOfficialExcursions extends Command
{
    protected $signature = 'museum:import-official-excursions
        {--apply : Create four verified source pages as private CMS drafts}
        {--children : Also create two genuine program landing pages in existing Children CMS sections}
        {--source= : Override local JSON for deterministic QA}';

    protected $description = 'Import museum excursion source pages into existing CMS as non-published editable drafts';

    private const SOURCES = [
        'excursion-overview' => [
            '/obzornaya-ekskursiya',
            '7ec96f65b314a8b403a7919d92b0a27a59bebe5ce8461d16a4c08e0da89a5b0c',
        ],
        'excursion-interactive' => [
            '/interaktivnye-zanyatiya',
            'a94989b72214d55506659220432b8568ad9a0fd1a1ab361f4e2eb2472b4d1c84',
        ],
        'excursion-thematic' => [
            '/tematicheskie-ekskursii',
            'b2994b3ffafee97e4c89e38a5d37f5864f07ee850f880844a0456113f92fac67',
        ],
        'excursion-theatrical' => [
            '/teatralizovannye-ekskursii',
            '8e79923308965c76b21b2fbb4742f345260ca5daefb875116cfbd70000db3e86',
        ],
    ];

    public function handle(): int
    {
        if ($this->option('apply') && app()->environment('production')) {
            $this->error('Bulk source migration forbidden on production.');
            return self::FAILURE;
        }
        try {
            $path = $this->option('source') ?: base_path('../web/src/data/official-excursion-pages.json');
            $data = json_decode((string) file_get_contents($path), true, flags: JSON_THROW_ON_ERROR);
            if (($data['source'] ?? null) !== 'https://muzei-xleb.ru'
                || ($data['count'] ?? null) !== 4
                || ! is_array($data['pages'] ?? null) || count($data['pages']) !== 4) {
                throw new RuntimeException('Expected four official museum excursion sources');
            }
            $plan = [];
            foreach ($data['pages'] as $page) {
                $slug = $page['cms_slug'] ?? null;
                $spec = is_string($slug) ? (self::SOURCES[$slug] ?? null) : null;
                if ($spec === null || isset($plan[$slug])
                    || ($page['path'] ?? null) !== $spec[0]
                    || ($page['source_url'] ?? null) !== 'https://muzei-xleb.ru'.$spec[0]
                    || ($page['html_sha256'] ?? null) !== $spec[1]
                    || ! is_string($page['html'] ?? null)
                    || hash('sha256', $page['html']) !== $spec[1]
                    || ! is_string($page['title'] ?? null)
                    || mb_strlen(trim($page['title'])) < 6
                    || ! is_numeric($page['text_length'] ?? null)
                    || $page['text_length'] < 100
                    || ($page['photos_rights_confirmed'] ?? null) !== false
                    || ! is_string($page['captured_utc'] ?? null)
                    || ! preg_match('/^\d{4}-\d\d-\d\dT/', $page['captured_utc'])) {
                    throw new RuntimeException('Museum excursion source or signature is not valid: '.(string) $slug);
                }
                $section = MuseumSection::where('slug', $slug)->first();
                if (! $section || $section->legacy_path !== $spec[0]) {
                    throw new RuntimeException('CMS excursion section missing or incorrectly mapped: '.$slug);
                }
                $existing = MuseumEntry::where('slug', $slug)->first();
                if ($existing && ($existing->type !== 'page'
                    || $existing->museum_section_id !== $section->id)) {
                    throw new RuntimeException('Existing excursion page belongs to another editor: '.$slug);
                }
                $plan[$slug] = compact('page', 'section', 'existing');
            }
            if (count($plan) !== count(self::SOURCES)) {
                throw new RuntimeException('Missing exact excursion source from official manifest');
            }
            $children = [];
            if ($this->option('children')) {
                foreach ([
                    'children-interactive' => 'excursion-interactive',
                    'children-thematic' => 'excursion-thematic',
                ] as $slug => $sourceSlug) {
                    $section = MuseumSection::where('slug', $slug)->first();
                    $sourcePage = $plan[$sourceSlug]['page'];
                    if (! $section || $section->parent?->slug !== 'children'
                        || $section->legacy_path !== null) {
                        throw new RuntimeException('Missing exact children section: '.$slug);
                    }
                    $existing = MuseumEntry::where('slug', $slug)->first();
                    if ($existing && ($existing->type !== 'page'
                        || $existing->museum_section_id !== $section->id)) {
                        throw new RuntimeException('Unrelated editor owns children slug: '.$slug);
                    }
                    $children[$slug] = compact('section', 'sourcePage', 'existing');
                }
            }
            foreach ($plan as $slug => $item) {
                $this->line(($item['existing'] ? 'KEEP EDITOR' : 'NEW PRIVATE DRAFT')
                    .' '.$slug.' ← '.$item['page']['source_url']);
            }
            foreach ($children as $slug => $item) {
                $this->line(($item['existing'] ? 'KEEP EDITOR' : 'NEW CHILDREN DRAFT')
                    .' '.$slug.' ← '.$item['sourcePage']['source_url']);
            }
            if (! $this->option('apply')) {
                $this->info('Dry run: no CMS changes.');
                return self::SUCCESS;
            }
            DB::transaction(function () use ($plan, $children): void {
                foreach ($plan as $slug => $item) {
                    $page = $item['page'];
                    MuseumEntry::firstOrCreate(['slug' => $slug], [
                        'museum_section_id' => $item['section']->id,
                        'type' => 'page',
                        'title' => mb_substr($page['title'], 0, 255),
                        'h1' => mb_substr($page['title'], 0, 255),
                        'excerpt' => 'Источник: '.$page['source_url'].'; снимок: '.$page['captured_utc'],
                        'body' => $page['html'],
                        'status' => 'draft',
                        'published_at' => null,
                    ]);
                }
                foreach ($children as $slug => $item) {
                    $page = $item['sourcePage'];
                    $url = htmlspecialchars($page['source_url'], ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
                    MuseumEntry::firstOrCreate(['slug' => $slug], [
                        'museum_section_id' => $item['section']->id,
                        'type' => 'page',
                        'title' => $item['section']->title,
                        'h1' => $item['section']->title,
                        'excerpt' => 'Источник: '.$page['source_url'].'; снимок: '.$page['captured_utc'],
                        'body' => '<p>В этом разделе представлены программы из действующего '
                            .'официального каталога музея. Возрастные ограничения и условия участия '
                            .'уточняйте по описаниям конкретных экскурсий.</p><p><a href="'.$url.'">'
                            .'Официальный музейный каталог программ</a></p>',
                        'status' => 'draft',
                        'published_at' => null,
                    ]);
                }
            });
            $this->info('Original excursion and selected children sections are private MoonShine drafts; no publication, photos or new sales.');
            return self::SUCCESS;
        } catch (Throwable $error) {
            $this->error('Import refused: '.$error->getMessage());
            return self::FAILURE;
        }
    }
}
