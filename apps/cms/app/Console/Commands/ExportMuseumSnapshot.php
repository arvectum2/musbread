<?php

namespace App\Console\Commands;

use App\Models\MuseumEvent;
use App\Models\MuseumEntry;
use Illuminate\Console\Command;

class ExportMuseumSnapshot extends Command
{
    protected $signature = 'museum:export {--output= : Path to generated JSON} {--manifest= : Path to integrity manifest}';
    protected $description = 'Publish approved CMS content into an offline static-site snapshot';

    public function handle(): int
    {
        $output = $this->option('output') ?: base_path('../web/src/data/published.json');
        $manifest = $this->option('manifest') ?: base_path('../web/public/snapshot-manifest.json');

        $events = MuseumEvent::query()
            ->public()
            ->orderBy('starts_at')
            ->orderBy('slug')
            ->get()
            ->map(fn (MuseumEvent $event) => [
                'slug' => $event->slug, 'title' => $event->title,
                'category' => $event->category,
                'date' => $event->starts_at->format('Y-m-d'),
                'excerpt' => $event->excerpt, 'body' => $event->body,
            ])->all();

        $entries = MuseumEntry::query()
            ->public()
            ->orderBy('type')
            ->orderBy('sort_order')
            ->orderBy('slug')
            ->get()
            ->map(fn (MuseumEntry $entry) => [
                'type' => $entry->type,
                'slug' => $entry->slug,
                'title' => $entry->title,
                'h1' => $entry->h1,
                'parent_slug' => $entry->parent_slug,
                'excerpt' => $entry->excerpt,
                'body' => $entry->body,
                'seo_title' => $entry->seo_title,
                'seo_description' => $entry->seo_description,
                'sort_order' => $entry->sort_order,
            ])->all();

        // Public export intentionally excludes draft/private properties, role info and PII.
        $data = [
            'schema_version' => 1,
            'site' => [
                'name' => 'Музей Хлеба',
                'subtitle' => 'Демонстрационная версия · концепция не утверждена',
                'description' => 'Предконтрактный прототип информационного сайта музея.',
            ],
            'events' => $events,
            'entries' => $entries,
        ];
        // Match the Python fixture publisher canonical JSON serializer.
        $normalize = function ($obj) use (&$normalize) {
            if (! is_array($obj)) return $obj;
            if (array_is_list($obj)) return array_map($normalize, $obj);
            ksort($obj);
            return array_map($normalize, $obj);
        };
        $payload = json_encode($normalize($data), JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES | JSON_THROW_ON_ERROR)."\n";
        $audit = [
            'schema_version' => 1,
            'files' => ['published.json' => ['sha256' => hash('sha256', $payload), 'bytes' => strlen($payload)]],
            'event_count' => count($events),
            'entry_count' => count($entries),
        ];
        $manifestData = json_encode($normalize($audit), JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES | JSON_THROW_ON_ERROR)."\n";

        foreach ([[$output, $payload], [$manifest, $manifestData]] as [$target, $contents]) {
            if (! is_dir(dirname($target))) {
                mkdir(dirname($target), 0755, true);
            }
            $temporary = $target.'.tmp.'.getmypid();
            if (file_put_contents($temporary, $contents, LOCK_EX) === false || ! rename($temporary, $target)) {
                throw new \RuntimeException('Unable to publish snapshot file: '.$target);
            }
        }
        $this->info('Published '.count($events).' events and '.count($entries).' entries; SHA-256='.hash('sha256', $payload));
        return self::SUCCESS;
    }
}
