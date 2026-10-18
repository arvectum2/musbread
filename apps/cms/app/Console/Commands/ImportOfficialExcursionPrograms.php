<?php

namespace App\Console\Commands;

use App\Models\MuseumEntry;
use App\Models\MuseumSection;
use Illuminate\Console\Command;
use Illuminate\Support\Facades\DB;
use RuntimeException;
use Throwable;

/**
 * Source-verified real museum programs, not speculative schedules. The source
 * museum index contains 18 link occurrences, one duplicated URL. Capture 17
 * separate official content pages, imported only as private CMS excursion drafts.
 */
final class ImportOfficialExcursionPrograms extends Command
{
    protected $signature = 'museum:import-official-excursion-programs
        {--apply : Save missing genuine museum program descriptions as private drafts}
        {--source= : Override private/source JSON for deterministic tests}';

    protected $description = 'Preview or import 17 verified original museum programs in existing excursion CMS';

    private const INDEX_HASHES = [
        'excursion-interactive' => 'a94989b72214d55506659220432b8568ad9a0fd1a1ab361f4e2eb2472b4d1c84',
        'excursion-thematic' => 'b2994b3ffafee97e4c89e38a5d37f5864f07ee850f880844a0456113f92fac67',
        'excursion-theatrical' => '8e79923308965c76b21b2fbb4742f345260ca5daefb875116cfbd70000db3e86',
    ];

    // Pinned after full capture via Mac mini. Exact ordered URL + HTML sha256,
    // not just hashes generated from an attacker-modified fixture.
    private const SOURCE_SET_HASH = '028d57fc41f7e6baf24c9b4bc63a0551ce81cead4171664a40a6497ab0108bf9';

    public function handle(): int
    {
        if ($this->option('apply') && app()->environment('production')) {
            $this->error('Live source bulk import forbidden in production.');
            return self::FAILURE;
        }

        try {
            $path = $this->option('source') ?: base_path('../web/src/data/official-excursion-programs.json');
            $data = json_decode((string) file_get_contents($path), true, flags: JSON_THROW_ON_ERROR);
            if (($data['source'] ?? null) !== 'https://muzei-xleb.ru'
                || ($data['count'] ?? null) !== 17
                || ! is_array($data['programs'] ?? null)
                || count($data['programs']) !== 17) {
                throw new RuntimeException('Expected 17 distinct original museum program records');
            }
            $fingerprint = [];
            foreach ($data['programs'] as $program) {
                $fingerprint[] = (string) ($program['source_url'] ?? '').'|'
                    .(string) ($program['html_sha256'] ?? '');
            }
            if (hash('sha256', implode("\n", $fingerprint)) !== self::SOURCE_SET_HASH) {
                throw new RuntimeException('Pinned museum program source set changed');
            }

            $sourceIndex = json_decode(
                (string) file_get_contents(base_path('../web/src/data/official-excursion-pages.json')),
                true, flags: JSON_THROW_ON_ERROR);
            $index = [];
            foreach ($sourceIndex['pages'] ?? [] as $page) {
                if (! is_array($page)) continue;
                $index[$page['cms_slug']] = $page;
            }
            $seen = [];
            $plan = [];
            $perCategory = [];
            foreach ($data['programs'] as $program) {
                $url = $program['source_url'] ?? '';
                $slug = $program['slug'] ?? '';
                $category = $program['category_slug'] ?? '';
                $pathName = $program['path'] ?? '';
                $title = $program['title'] ?? '';
                $source = self::INDEX_HASHES[$category] ?? null;
                $section = MuseumSection::where('slug', $category)->first();
                $categoryIndex = $index[$category] ?? null;
                if (! is_string($url) || ! preg_match('#^https://muzei-xleb\.ru/ekskursii/[a-z0-9-]+$#D', $url)
                    || ! is_string($slug) || $slug !== 'museum-tour-'.substr($url, strlen('https://muzei-xleb.ru/ekskursii/'))
                    || $pathName !== parse_url($url, PHP_URL_PATH)
                    || isset($seen[$slug])
                    || ! $source || ! is_array($categoryIndex)
                    || ($categoryIndex['html_sha256'] ?? null) !== $source
                    || hash('sha256', $categoryIndex['html']) !== $source
                    || ! str_contains($categoryIndex['html'], 'href="'.$url.'"')
                    || ! $section || $section->legacy_path !== $categoryIndex['path']
                    || ! is_string($title) || mb_strlen(trim($title)) < 6
                    || ! is_string($program['html'] ?? null)
                    || mb_strlen($program['html']) < 100
                    || hash('sha256', $program['html']) !== $program['html_sha256']
                    || ($program['photos_rights_confirmed'] ?? true) !== false
                    || ! is_string($program['captured_utc'] ?? null)
                    || ! preg_match('/^\d{4}-\d\d-\d\dT/', $program['captured_utc'])) {
                    throw new RuntimeException('Invalid verified program or CMS category: '.(string) $slug);
                }
                $existing = MuseumEntry::where('slug', $slug)->first();
                if ($existing && ($existing->type !== 'excursion'
                    || $existing->museum_section_id !== $section->id)) {
                    throw new RuntimeException('Unrelated editor owns this museum excursion slug: '.$slug);
                }
                $seen[$slug] = true;
                $perCategory[$category] = ($perCategory[$category] ?? 0) + 1;
                $plan[] = compact('slug', 'program', 'section', 'existing')
                    + ['sort_order' => $perCategory[$category]];
            }
            if ($perCategory !== [
                'excursion-interactive' => 6,
                'excursion-thematic' => 9,
                'excursion-theatrical' => 2,
            ]) {
                throw new RuntimeException('Expected 6/9/2 original distinct program descriptions');
            }

            foreach ($plan as $row) {
                $this->line(($row['existing'] ? 'KEEP EDITOR' : 'NEW EXCURSION DRAFT').' '
                    .$row['slug'].' ← '.$row['program']['source_url']);
            }
            if (! $this->option('apply')) {
                $this->info('Dry run: not a museum-approved schedule; no database writes.');
                return self::SUCCESS;
            }
            DB::transaction(function () use ($plan): void {
                foreach ($plan as $row) {
                    $p = $row['program'];
                    $url = htmlspecialchars($p['source_url'], ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
                    $plain = trim(preg_replace('/\s+/u', ' ', strip_tags($p['html'])));
                    $excerpt = mb_substr($plain, 0, 240);
                    MuseumEntry::firstOrCreate(['slug' => $row['slug']], [
                        'type' => 'excursion',
                        'museum_section_id' => $row['section']->id,
                        'title' => mb_substr($p['title'], 0, 255),
                        'h1' => mb_substr($p['title'], 0, 255),
                        'excerpt' => $excerpt,
                        'body' => $p['html'].'<p><a href="'.$url.'">'
                            .'Официальный музейный первоисточник программы ↗</a></p>',
                        'sort_order' => $row['sort_order'],
                        'status' => 'draft',
                        'published_at' => null,
                    ]);
                }
            });
            $this->info('17 real source-linked programs available as private MoonShine excursion drafts.');
            return self::SUCCESS;
        } catch (Throwable $error) {
            $this->error('Excursion import refused: '.$error->getMessage());
            return self::FAILURE;
        }
    }
}
