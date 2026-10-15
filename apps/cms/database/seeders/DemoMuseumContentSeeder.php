<?php

namespace Database\Seeders;

use App\Models\MuseumEvent;
use App\Models\MuseumEntry;
use Illuminate\Database\Seeder;

class DemoMuseumContentSeeder extends Seeder
{
    public function run(): void
    {
        if (app()->environment('production')) {
            throw new \RuntimeException('Demo museum events must never be seeded in production.');
        }
        $file = dirname(__DIR__, 3).'/../fixtures/content.json';
        if (! is_file($file)) {
            throw new \RuntimeException('Demo fixture not found');
        }
        $fixture = json_decode(file_get_contents($file), true, flags: JSON_THROW_ON_ERROR);
        $events = $fixture['events'];
        foreach ($events as $event) {
            MuseumEvent::query()->updateOrCreate(
                ['slug' => $event['slug']],
                [
                    'title' => $event['title'], 'category' => $event['category'],
                    'starts_at' => $event['date'], 'excerpt' => $event['excerpt'],
                    'body' => $event['body'], 'status' => 'published',
                    'published_at' => now()->subDay(),
                ]
            );
        }
        foreach ($fixture['entries'] ?? [] as $entry) {
            MuseumEntry::query()->updateOrCreate(
                ['slug' => $entry['slug']],
                array_merge($entry, ['status' => 'published', 'published_at' => now()->subDay()])
            );
        }
    }
}
