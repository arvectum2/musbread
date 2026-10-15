<?php

namespace Database\Seeders;

use App\Models\MuseumRequest;
use App\Models\MuseumSection;
use Illuminate\Database\Seeder;

/**
 * Opt-in synthetic records for internal UI demos only; never any real visitor
 * name/email/phone/message. Prohibited in the customer's production system.
 */
final class DemoMuseumRequestsSeeder extends Seeder
{
    public function run(): void
    {
        if (app()->environment('production')) {
            throw new \RuntimeException('Never seed synthetic visitor requests in production.');
        }

        $visitors = MuseumSection::query()->where('slug', 'visitors')->first();
        $excursions = MuseumSection::query()->where('slug', 'excursions-guide')->first();
        if ($visitors === null || $excursions === null) {
            throw new \RuntimeException('Run ReferenceMuseumSectionsSeeder first.');
        }

        MuseumRequest::query()->firstOrCreate(
            [
                'type' => 'feedback', 'topic' => 'accessibility',
                'museum_section_id' => $visitors->id, 'origin' => 'internal_demo',
            ],
            ['status' => 'new'],
        );

        MuseumRequest::query()->firstOrCreate(
            [
                'type' => 'excursion', 'topic' => 'excursion_group',
                'museum_section_id' => $excursions->id, 'origin' => 'internal_demo',
            ],
            ['preferred_date' => '2026-11-20', 'group_size' => 12, 'status' => 'new'],
        );
    }
}
