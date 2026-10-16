<?php

declare(strict_types=1);

namespace Tests\Feature;

use App\Models\MuseumEntry;
use App\Models\MuseumEvent;
use App\Support\MuseumContentPreflight;
use App\Support\MuseumEntryPublicationState;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Carbon;
use Tests\TestCase;

final class MuseumPublicationExpiryTest extends TestCase
{
    use RefreshDatabase;

    private function material(string $slug, array $overrides = []): MuseumEntry
    {
        return MuseumEntry::create(array_merge([
            'slug' => $slug, 'type' => 'news', 'title' => 'Новость '.$slug,
            'excerpt' => 'Анонс', 'body' => '<p>Текст '.$slug.'</p>',
            'status' => 'published', 'published_at' => '2026-10-16 10:00:00',
        ], $overrides));
    }

    private function event(string $slug, array $overrides = []): MuseumEvent
    {
        return MuseumEvent::create(array_merge([
            'slug' => $slug, 'title' => 'Мероприятие '.$slug,
            'category' => 'Выставка', 'starts_at' => '2026-11-09',
            'excerpt' => 'Анонс', 'body' => '<p>Программа '.$slug.'</p>',
            'status' => 'published', 'published_at' => '2026-10-16 10:00:00',
        ], $overrides));
    }

    private function setClock(string $time): void
    {
        $this->travelTo(Carbon::parse($time, 'UTC'));
    }

    /** Export to an isolated path; never overwrite the actual public snapshot. */
    private function snapshot(): array
    {
        $dir = storage_path('framework/testing');
        if (! is_dir($dir)) mkdir($dir, 0700, true);
        $out = $dir.'/tz234-ttl-snapshot.json';
        $manifest = $dir.'/tz234-ttl-manifest.json';
        try {
            $this->artisan('museum:export', ['--output' => $out, '--manifest' => $manifest,
                '--preflight-strict' => true])->assertSuccessful();
            $data = json_decode(file_get_contents($out), true, flags: JSON_THROW_ON_ERROR);
            $audit = json_decode(file_get_contents($manifest), true, flags: JSON_THROW_ON_ERROR);
            $this->assertSame(hash_file('sha256', $out), $audit['files']['published.json']['sha256']);
            return $data;
        } finally {
            @unlink($out);
            @unlink($manifest);
        }
    }

    public function test_expiration_boundary_removes_pages_and_events_but_preserves_private_database_history(): void
    {
        $this->setClock('2026-10-16 12:00:00');
        $entry = $this->material('expired-page', ['unpublish_at' => '2026-10-16 13:00:00']);
        $event = $this->event('expired-event', ['unpublish_at' => '2026-10-16 13:00:00']);
        $permanent = $this->material('permanent-news');
        $data = $this->snapshot();
        $this->assertEqualsCanonicalizing(['expired-page', 'permanent-news'], array_column($data['entries'], 'slug'));
        $this->assertSame(['expired-event'], array_column($data['events'], 'slug'));

        $this->setClock('2026-10-16 12:59:59');
        $this->assertTrue(MuseumEntry::query()->public()->whereKey($entry->id)->exists());
        $this->assertTrue(MuseumEvent::query()->public()->whereKey($event->id)->exists());
        $this->setClock('2026-10-16 13:00:00');
        $this->assertFalse(MuseumEntry::query()->public()->whereKey($entry->id)->exists());
        $this->assertFalse(MuseumEvent::query()->public()->whereKey($event->id)->exists());
        $this->assertTrue(MuseumEntry::query()->public()->whereKey($permanent->id)->exists());
        $this->assertTrue(MuseumEntry::query()->whereKey($entry->id)->exists());
        $this->assertTrue(MuseumEvent::query()->whereKey($event->id)->exists());
        $after = $this->snapshot();
        $this->assertSame(['permanent-news'], array_column($after['entries'], 'slug'));
        $this->assertSame([], $after['events']);
        $report = app(MuseumContentPreflight::class)->report();
        $this->assertSame('expired', collect($report['records'])->firstWhere('id', $entry->id)['state']);
        $this->assertSame('expired', collect($report['events'])->firstWhere('id', $event->id)['state']);
        $this->assertSame(1, $report['ready']);
        $this->assertSame(0, $report['events_ready']);
        $this->assertTrue(MuseumEntryPublicationState::apply(MuseumEntry::query(), 'expired')->whereKey($entry->id)->exists());
        $this->assertFalse(MuseumEntryPublicationState::apply(MuseumEntry::query(), 'ready')->whereKey($entry->id)->exists());
    }

    public function test_scheduled_start_and_expiry_do_not_create_an_early_public_window(): void
    {
        $this->setClock('2026-10-16 12:00:00');
        $entry = $this->material('scheduled-window', [
            'published_at' => '2026-10-16 12:30:00', 'unpublish_at' => '2026-10-16 15:00:00',
        ]);
        $event = $this->event('scheduled-window-event', [
            'published_at' => '2026-10-16 12:30:00', 'unpublish_at' => '2026-10-16 15:00:00',
        ]);
        $this->assertSame('scheduled', collect(app(MuseumContentPreflight::class)->report()['records'])->firstWhere('id', $entry->id)['state']);
        $this->assertSame([], $this->snapshot()['entries']);
        $this->assertFalse(MuseumEvent::query()->public()->whereKey($event->id)->exists());
        $this->setClock('2026-10-16 12:30:00');
        $this->assertSame(['scheduled-window'], array_column($this->snapshot()['entries'], 'slug'));
        $this->assertTrue(MuseumEvent::query()->public()->whereKey($event->id)->exists());
        $this->setClock('2026-10-16 15:00:00');
        $this->assertSame([], $this->snapshot()['entries']);
        $this->assertSame([], $this->snapshot()['events']);
    }

    public function test_expired_link_target_must_be_removed_from_active_content_before_export(): void
    {
        $this->setClock('2026-10-16 12:00:00');
        $target = $this->material('temporarily-linked', [
            'unpublish_at' => '2026-10-16 13:00:00',
        ]);
        $source = $this->material('permanent-source', [
            'body' => '<p>Читайте <a href="/news/temporarily-linked/">другую новость</a>.</p>',
        ]);
        $this->artisan('museum:preflight', ['--strict' => true])->assertSuccessful();
        $this->setClock('2026-10-16 13:00:00');
        $report = app(MuseumContentPreflight::class)->report();
        $issues = collect($report['records'])->firstWhere('id', $source->id)['issues'];
        $this->assertContains('internal_link_unavailable', array_column($issues, 'code'));
        $this->assertSame('expired', collect($report['records'])->firstWhere('id', $target->id)['state']);
        $this->artisan('museum:preflight', ['--strict' => true])->assertFailed();
        // Avoid replacing a valid public snapshot with broken outbound links:
        // copy editors remove or rewrite the expired URL before the next export.
        $source->update(['body' => '<p>Архивная информация временно недоступна.</p>']);
        $this->artisan('museum:preflight', ['--strict' => true])->assertSuccessful();
        $this->assertSame(['permanent-source'], array_column($this->snapshot()['entries'], 'slug'));
    }

    public function test_invalid_publication_window_is_detected_before_strict_export(): void
    {
        $this->setClock('2026-10-16 12:00:00');
        $entry = $this->material('invalid-window', [
            'published_at' => '2026-10-16 11:30:00', 'unpublish_at' => '2026-10-16 11:15:00',
        ]);
        $event = $this->event('invalid-event-window', [
            'published_at' => '2026-10-16 11:30:00', 'unpublish_at' => '2026-10-16 11:15:00',
        ]);
        $record = collect(app(MuseumContentPreflight::class)->report()['records'])->firstWhere('id', $entry->id);
        $eventRecord = collect(app(MuseumContentPreflight::class)->report()['events'])->firstWhere('id', $event->id);
        $this->assertContains('publication_window_invalid', array_column($record['issues'], 'code'));
        $this->assertContains('event_publication_window_invalid', array_column($eventRecord['issues'], 'code'));
        $this->assertSame('expired', $record['state']);
        $this->assertSame('expired', $eventRecord['state']);
        $this->assertSame([], $this->snapshot()['entries']);
    }
}
