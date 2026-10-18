<?php

namespace App\Console\Commands;

use App\Models\MuseumEntry;
use App\Models\MuseumSection;
use Illuminate\Console\Command;
use Illuminate\Support\Facades\DB;
use RuntimeException;
use Throwable;

/**
 * Current museum pages are factual evidence for author-provided FAQ questions.
 * Import is a private, opt-in draft baseline. Never an official signed rulebook.
 */
final class ImportOfficialVisitorFaq extends Command
{
    protected $signature = 'museum:import-official-visitor-faq
        {--apply : Create one private editable FAQ page (never publish)}
        {--source= : Override local generated FAQ file for deterministic testing}';

    protected $description = 'Preview or import nine museum-source-backed FAQ answers as a private MoonShine draft';

    public function handle(): int
    {
        if ($this->option('apply') && app()->environment('production')) {
            $this->error('Production FAQ bulk import is not allowed; use reviewed CMS editorial actions.');
            return self::FAILURE;
        }
        try {
            $path = $this->option('source') ?: base_path('../web/src/data/official-visitor-faq.json');
            $data = json_decode((string) file_get_contents($path), true, flags: JSON_THROW_ON_ERROR);
            if (($data['source'] ?? null) !== 'https://muzei-xleb.ru'
                || ($data['count'] ?? null) !== 9 || ! is_array($data['questions'] ?? null)
                || count($data['questions']) !== 9) {
                throw new RuntimeException('FAQ source/count mismatch');
            }
            $original = json_decode(
                (string) file_get_contents(base_path('../web/src/data/official-page-snapshots.json')),
                true, flags: JSON_THROW_ON_ERROR
            );
            $extras = json_decode(
                (string) file_get_contents(base_path('../web/src/data/official-visitor-guidance.json')),
                true, flags: JSON_THROW_ON_ERROR
            );
            if (($original['source'] ?? null) !== $data['source']
                || ($extras['source'] ?? null) !== $data['source']) {
                throw new RuntimeException('Official museum source mismatch');
            }
            $pages = [];
            foreach (array_merge($original['pages'], $extras['pages']) as $page) {
                $pages[$page['path']] = $page;
            }
            $seen = [];
            $body = '';
            foreach ($data['questions'] as $entry) {
                $id = $entry['id'] ?? null;
                $pathName = $entry['source_path'] ?? null;
                $page = is_string($pathName) ? ($pages[$pathName] ?? null) : null;
                $sourceHash = $entry['source_html_sha256'] ?? null;
                $answer = $entry['answer'] ?? null;
                $question = $entry['question'] ?? null;
                if (! is_string($id) || ! preg_match('/^[a-z-]{3,32}$/D', $id)
                    || isset($seen[$id]) || ! is_array($page)
                    || ! is_string($sourceHash) || $sourceHash !== $page['html_sha256']
                    || hash('sha256', $page['html']) !== $page['html_sha256']
                    || ($entry['source_url'] ?? null) !== $page['source_url']
                    || ! str_starts_with((string) $page['source_url'], 'https://muzei-xleb.ru/')
                    || ! is_string($answer) || mb_strlen(trim($answer)) < 45
                    || mb_strlen($answer) > 1500
                    || ! is_string($question) || mb_strlen(trim($question)) < 15
                    || mb_strlen($question) > 250
                    || ! is_array($entry['source_phrases'] ?? null)
                    || count($entry['source_phrases']) < 1) {
                    throw new RuntimeException('FAQ source/signature/length/identity mismatch: '.(string) $id);
                }
                $sourceText = preg_replace('/\s+/u', ' ',
                    html_entity_decode(strip_tags($page['html']), ENT_QUOTES | ENT_HTML5, 'UTF-8'));
                foreach ($entry['source_phrases'] as $phrase) {
                    if (! is_string($phrase) || mb_strlen($phrase) < 6
                        || ! str_contains($sourceText, trim(preg_replace('/\s+/u', ' ', $phrase)))) {
                        throw new RuntimeException('FAQ claim not grounded in museum source: '.$id);
                    }
                }
                $seen[$id] = true;
                $q = htmlspecialchars(trim($question), ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
                $a = htmlspecialchars(trim($answer), ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
                $url = htmlspecialchars($page['source_url'], ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
                $body .= '<h2>'.$q.'</h2><p>'.$a.'</p><p><a href="'.$url.'">'
                    .'Официальный музейный первоисточник</a></p>'."\n";
            }
            $section = MuseumSection::where('slug', 'faq')->first();
            if (! $section) {
                throw new RuntimeException('Existing MuseumSection faq not found');
            }
            $existing = MuseumEntry::where('slug', 'faq')->first();
            if ($existing && ($existing->type !== 'page'
                || $existing->museum_section_id !== $section->id)) {
                throw new RuntimeException('An unrelated editor owns the FAQ slug');
            }
            $this->info('Verified nine answers against archived signed museum sources; existing editor changes preserved.');
            if (! $this->option('apply')) {
                $this->info('Dry run: no local CMS changes.');
                return self::SUCCESS;
            }
            DB::transaction(function () use ($section, $body): void {
                MuseumEntry::firstOrCreate(['slug' => 'faq'], [
                    'type' => 'page',
                    'museum_section_id' => $section->id,
                    'title' => 'Частые вопросы',
                    'h1' => 'Частые вопросы о посещении музея',
                    'excerpt' => 'Девять подготовленных по действующему сайту музея ответов; источник указан под каждым.',
                    'body' => $body,
                    'status' => 'draft',
                    'published_at' => null,
                ]);
            });
            $this->info('FAQ draft is editable in MoonShine and NOT published.');
            return self::SUCCESS;
        } catch (Throwable $error) {
            $this->error('FAQ import refused: '.$error->getMessage());
            return self::FAILURE;
        }
    }
}
