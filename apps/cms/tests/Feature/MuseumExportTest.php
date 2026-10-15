<?php

namespace Tests\Feature;

use App\Models\MuseumEvent;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Tests\TestCase;

class MuseumExportTest extends TestCase
{
    use RefreshDatabase;

    public function test_only_approved_records_leave_the_private_cms(): void
    {
        $fixture = [
            'title' => 'Example', 'category' => 'Test', 'starts_at' => '2026-11-17',
            'excerpt' => 'Excerpt', 'body' => 'Description',
        ];
        MuseumEvent::create(array_merge($fixture, [
            'slug' => 'private-draft', 'status' => 'draft',
        ]));
        MuseumEvent::create(array_merge($fixture, [
            'slug' => 'future-private', 'status' => 'published',
            'published_at' => now()->addDay(),
        ]));
        MuseumEvent::create(array_merge($fixture, [
            'slug' => 'public-event', 'status' => 'published',
            'published_at' => now()->subDay(),
        ]));

        $out = storage_path('framework/testing/snapshot.json');
        $manifest = storage_path('framework/testing/manifest.json');
        $this->artisan('museum:export', ['--output' => $out, '--manifest' => $manifest])->assertSuccessful();
        $data = json_decode(file_get_contents($out), true, flags: JSON_THROW_ON_ERROR);
        $this->assertCount(1, $data['events']);
        $this->assertSame('public-event', $data['events'][0]['slug']);
        $this->assertStringNotContainsString('private-draft', file_get_contents($out));
        $this->assertStringNotContainsString('future-private', file_get_contents($out));
        $audit = json_decode(file_get_contents($manifest), true, flags: JSON_THROW_ON_ERROR);
        $this->assertSame(hash_file('sha256', $out), $audit['files']['published.json']['sha256']);
        unlink($out);
        unlink($manifest);
    }
}
