<?php

namespace App\Console\Commands;

use App\Models\MuseumEntry;
use App\Models\MuseumSection;
use Illuminate\Console\Command;
use Illuminate\Support\Facades\DB;
use RuntimeException;
use Throwable;

/**
 * Imports existing public master-class descriptions. The museum does not
 * publish a dedicated adult programme: preserve that uncertainty. No mock
 * dates, media, prices or sale forms. 12 workshop records shared by two routes.
 */
final class ImportOfficialWorkshops extends Command
{
    protected $signature = 'museum:import-official-workshops
        {--apply : Create twelve source-backed workshop descriptions and two private landing pages}
        {--source= : Override local source JSON only for regression tests}';

    protected $description = 'Source-verified master-class catalog for children and adults, using existing CMS only';

    private const INDEX_SHA = '196452de05f3132dc0dd943cf00e46dc5222c2545e27a4927dd5d4fc98707193';
    private const SOURCE_SET_SHA = 'e7b759aa76d65fcf455a8fba8f02f4955b29f6ea2e296c7c4956188ecee6800d';

    public function handle(): int
    {
        if ($this->option('apply') && app()->environment('production')) {
            $this->error('Production source bulk import disabled. Approve/edit content individually.');
            return self::FAILURE;
        }
        try {
            $path = $this->option('source') ?: base_path('../web/src/data/official-workshop-pages.json');
            $data = json_decode((string) file_get_contents($path), true, flags: JSON_THROW_ON_ERROR);
            if (($data['source'] ?? null) !== 'https://muzei-xleb.ru'
                || ($data['count'] ?? null) !== 12
                || ! is_array($data['programs'] ?? null)
                || count($data['programs']) !== 12) {
                throw new RuntimeException('Expected 12 original museum master classes');
            }
            $index = $data['index'] ?? null;
            if (! is_array($index)
                || ($index['source_url'] ?? '') !== 'https://muzei-xleb.ru/master-klassy'
                || ! is_string($index['html'] ?? null)
                || hash('sha256', $index['html']) !== self::INDEX_SHA
                || ($index['html_sha256'] ?? null) !== self::INDEX_SHA) {
                throw new RuntimeException('Official museum master-class source index changed');
            }
            $set = [];
            foreach ($data['programs'] as $p) {
                $set[] = ($p['source_url'] ?? '').'|'.($p['html_sha256'] ?? '');
            }
            if (hash('sha256', implode("\n", $set)) !== self::SOURCE_SET_SHA) {
                throw new RuntimeException('Pinned museum master-class program list changed');
            }
            $child = MuseumSection::where('slug', 'children-workshops')->first();
            $adult = MuseumSection::where('slug', 'excursion-workshops-adults')->first();
            if (! $child || $child->parent?->slug !== 'children'
                || $child->legacy_path !== null
                || ! $adult || $adult->parent?->slug !== 'excursions-guide'
                || $adult->legacy_path !== null) {
                throw new RuntimeException('Workshop CMS sections missing or parent mapping changed');
            }
            $seen = [];
            $plan = [];
            foreach ($data['programs'] as $i => $p) {
                $url = $p['source_url'] ?? '';
                $pathName = $p['path'] ?? '';
                $slug = $p['slug'] ?? '';
                $title = $p['title'] ?? '';
                if (! is_string($url)
                    || ! preg_match('#^https://muzei-xleb\.ru/(?:master-klassy|ekskursii)/[a-z0-9-]+$#D', $url)
                    || $pathName !== parse_url($url, PHP_URL_PATH)
                    || ! is_string($slug) || $slug !== 'museum-workshop-'.basename($pathName)
                    || isset($seen[$slug])
                    || ! str_contains($index['html'], 'href="'.$url.'"')
                    || ! is_string($title) || mb_strlen(trim($title)) < 4
                    || ! is_string($p['html'] ?? null) || strlen($p['html']) < 90
                    || ($p['html_sha256'] ?? null) !== hash('sha256', $p['html'])
                    || ($p['photos_rights_confirmed'] ?? null) !== false
                    || ! is_string($p['captured_utc'] ?? null)
                    || ! preg_match('/^\d{4}-\d\d-\d\dT/', $p['captured_utc'])
                    || ! is_string($p['intro'] ?? null) || mb_strlen($p['intro']) < 40) {
                    throw new RuntimeException('Workshop source tampering or missing fact: '.(string) $slug);
                }
                $existing = MuseumEntry::where('slug', $slug)->first();
                if ($existing && ($existing->type !== 'page'
                    || $existing->museum_section_id !== $child->id)) {
                    throw new RuntimeException('Unrelated editor owns a workshop slug: '.$slug);
                }
                $seen[$slug] = true;
                $plan[] = compact('p', 'slug', 'existing') + ['sort' => $i + 1];
            }
            $landings = [];
            foreach (['children-workshops' => $child, 'excursion-workshops-adults' => $adult] as $slug=>$section) {
                $existing = MuseumEntry::where('slug', $slug)->first();
                if ($existing && ($existing->type !== 'page'
                    || $existing->museum_section_id !== $section->id)) {
                    throw new RuntimeException('Unrelated editor owns workshop landing slug: '.$slug);
                }
                $landings[$slug] = compact('section','existing');
            }
            foreach ($plan as $row) {
                $this->line(($row['existing'] ? 'KEEP EDITOR' : 'NEW DRAFT').' '.$row['slug']);
            }
            foreach ($landings as $slug=>$row) {
                $this->line(($row['existing'] ? 'KEEP EDITOR' : 'NEW LANDING DRAFT').' '.$slug);
            }
            if (! $this->option('apply')) {
                $this->info('Dry run only: no CMS changes or fake workshop availability.');
                return self::SUCCESS;
            }
            DB::transaction(function () use ($plan, $landings, $child): void {
                foreach ($plan as $row) {
                    $p = $row['p'];
                    $url = htmlspecialchars($p['source_url'], ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
                    MuseumEntry::firstOrCreate(['slug'=>$row['slug']], [
                        'museum_section_id'=>$child->id,
                        'type'=>'page',
                        'title'=>mb_substr($p['title'],0,255),
                        'h1'=>mb_substr($p['title'],0,255),
                        'excerpt'=>$p['intro'],
                        'body'=>$p['html'].'<p><a href="'.$url.'">Официальное описание мастер-класса ↗</a></p>',
                        'sort_order'=>$row['sort'],
                        'status'=>'draft',
                        'published_at'=>null,
                    ]);
                }
                foreach ($landings as $slug=>$row) {
                    $adultPage = $slug === 'excursion-workshops-adults';
                    $text = $adultPage
                        ? 'На действующем сайте музея опубликован общий перечень мастер-классов без отдельного '
                            .'каталога для взрослых. Участие взрослых уточняйте у музея до записи.'
                        : 'Музей опубликовал 12 мастер-классов с возрастными ограничениями '
                            .'в оригинальных описаниях; даты и условия уточняйте у музея.';
                    MuseumEntry::firstOrCreate(['slug'=>$slug], [
                        'museum_section_id'=>$row['section']->id,
                        'type'=>'page',
                        'title'=>$row['section']->title,
                        'h1'=>$row['section']->title,
                        'excerpt'=>'Официальный музейный источник: https://muzei-xleb.ru/master-klassy',
                        'body'=>'<p>'.$text.'</p><p><a href="https://muzei-xleb.ru/master-klassy">'
                            .'Действующий каталог мастер-классов музея</a></p>',
                        'status'=>'draft',
                        'published_at'=>null,
                    ]);
                }
            });
            $this->info('12 private workshop content pages plus two private category landing pages; no photos or sales.');
            return self::SUCCESS;
        } catch (Throwable $error) {
            $this->error('Import refused: '.$error->getMessage());
            return self::FAILURE;
        }
    }
}
