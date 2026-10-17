<?php

namespace Database\Seeders;

use App\Models\MuseumSection;
use Illuminate\Database\Seeder;

/**
 * Draft structure extracted from public metadata at muzei-xleb.ru.
 * Opt-in only. Never rewrite an editor's existing section or seed on production.
 */
class ReferenceMuseumSectionsSeeder extends Seeder
{
    public function run(): void
    {
        if (app()->environment('production')) {
            throw new \RuntimeException('Reference demo content must not be seeded on production.');
        }
        $file = database_path('reference-museum-sections.json');
        $data = json_decode(file_get_contents($file), true, flags: JSON_THROW_ON_ERROR);
        if ($data['source'] !== 'https://muzei-xleb.ru/' || ! isset($data['sections'])) {
            throw new \RuntimeException('Unexpected site reference payload');
        }
        $groups = array_values(array_filter($data['sections'], static fn ($row) => $row['parent_slug'] === null));
        $children = array_values(array_filter($data['sections'], static fn ($row) => $row['parent_slug'] !== null));
        foreach ([$groups, $children] as $level) {
            foreach ($level as $row) {
                $parentId = $row['parent_slug'] === null ? null :
                    MuseumSection::query()->where('slug', $row['parent_slug'])->value('id');
                if ($row['parent_slug'] !== null && $parentId === null) {
                    throw new \RuntimeException('Missing reference parent '.$row['parent_slug']);
                }
                MuseumSection::query()->firstOrCreate(['slug' => $row['slug']], [
                    'title' => $row['title'],
                    'parent_id' => $parentId,
                    'sort_order' => $row['sort_order'],
                    'legacy_path' => $row['legacy_path'],
                    // Old-site leaves and seven TZ-required roots may be visible in the demo.
                    // Unsupported leaf placeholders remain private draft until approved.
                    'status' => ($row['legacy_path'] !== null || $row['parent_slug'] === null)
                        ? 'published' : 'draft',
                ]);
            }
        }
    }
}
