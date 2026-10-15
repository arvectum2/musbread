<?php

namespace Database\Seeders;

use App\Models\MuseumEvent;
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
        $events = json_decode(file_get_contents($file), true, flags: JSON_THROW_ON_ERROR)['events'];
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
    }
}
