<?php

namespace Tests\Feature;

use App\Models\MuseumEntry;
use App\Models\MuseumEvent;
use App\Models\MuseumPublicationRun;
use App\Models\MuseumSection;
use App\Support\MuseumPublicationDiff;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Artisan;
use MoonShine\Laravel\Models\MoonshineUser;
use MoonShine\Laravel\Models\MoonshineUserRole;
use Tests\TestCase;

class MuseumPublicationDiffTest extends TestCase
{
    use RefreshDatabase;

    private string $root;
    private string $originalDataHash;

    protected function setUp(): void
    {
        parent::setUp();
        $this->root = storage_path('framework/testing/diff-'.bin2hex(random_bytes(6)));
        mkdir($this->root, 0700, true);
        config(['museum.local_release_root' => $this->root.'/releases-root']);
        $this->originalDataHash = hash_file('sha256', base_path('../web/src/data/published.json'));
    }

    protected function tearDown(): void
    {
        if (isset($this->root) && is_dir($this->root)) {
            $iterator = new \RecursiveIteratorIterator(
                new \RecursiveDirectoryIterator($this->root, \FilesystemIterator::SKIP_DOTS),
                \RecursiveIteratorIterator::CHILD_FIRST);
            foreach ($iterator as $file) {
                if ($file->isDir() && ! $file->isLink()) rmdir($file->getPathname());
                else unlink($file->getPathname());
            }
            rmdir($this->root);
        }
        parent::tearDown();
    }

    private function article(string $slug, string $status = 'published', ?int $section = null): MuseumEntry
    {
        return MuseumEntry::create([
            'type' => 'news', 'slug' => $slug, 'title' => 'Новость '.$slug,
            'body' => '<p>Текст для '.$slug.'</p>', 'status' => $status,
            'museum_section_id' => $section,
        ]);
    }

    private function event(string $slug, string $status = 'published'): MuseumEvent
    {
        return MuseumEvent::create([
            'title' => 'Афиша '.$slug, 'slug' => $slug, 'category' => 'Выставка',
            'starts_at' => now()->addWeek()->toDateString(),
            'excerpt' => 'Анонс', 'body' => 'Программа', 'status' => $status,
        ]);
    }

    /** Seed a private baseline with a release-manifest authenticated snapshot SHA. */
    private function baseline(): string
    {
        $root = $this->root.'/releases-root';
        mkdir($root.'/private-snapshots', 0700, true);
        $snapshot = $this->root.'/baseline.json';
        $manifest = $this->root.'/baseline-manifest.json';
        $this->assertSame(0, Artisan::call('museum:export', [
            '--output' => $snapshot, '--manifest' => $manifest,
            '--media-output-dir' => $this->root.'/media',
            '--document-output-dir' => $this->root.'/documents',
        ]));
        $sha = hash_file('sha256', $snapshot);
        copy($snapshot, $root.'/private-snapshots/'.$sha.'.json');
        $files = [
            'index.html' => hash('sha256', 'private local release fixture'),
            'snapshot-manifest.json' => hash_file('sha256', $manifest),
        ];
        ksort($files);
        $id = substr(hash('sha256', json_encode($files, JSON_UNESCAPED_SLASHES)), 0, 16);
        $release = $root.'/releases/'.$id;
        mkdir($release, 0700, true);
        file_put_contents($release.'/index.html', 'private local release fixture');
        copy($manifest, $release.'/snapshot-manifest.json');
        file_put_contents($release.'/release-manifest.json', json_encode([
            'release' => $id, 'files' => $files,
        ]));
        symlink('releases/'.$id, $root.'/current');
        return $sha;
    }

    private function findDiffRow(array $data, string $group, string $key): array
    {
        $found = collect($data['groups'][$group])->firstWhere('key', $key);
        $this->assertNotNull($found, 'Expected '.$group.':'.$key);
        return $found;
    }

    public function test_baseline_unavailable_never_reports_false_additions_or_deletions(): void
    {
        $this->article('candidate-only');
        $admin = MoonshineUser::factory()->create();
        $this->actingAs($admin, 'moonshine')
            ->get(route('museum.content.compare'))->assertOk()
            ->assertSee('Подтверждённый локальный базовый снимок недоступен')
            ->assertDontSee('Добавится');
        $report = app(MuseumPublicationDiff::class)->report($admin);
        $this->assertFalse($report['baseline_available']);
        $this->assertSame([], $report['groups']);
        $this->assertSame($this->originalDataHash, hash_file('sha256', base_path('../web/src/data/published.json')));
    }

    public function test_added_changed_removed_and_unchanged_across_entries_events_and_sections(): void
    {
        $section = MuseumSection::create(['slug' => 'one', 'title' => 'Раздел один', 'status' => 'published']);
        $stable = $this->article('stable');
        $changed = $this->article('changed', section: $section->id);
        $removed = $this->article('removed');
        $eventStable = $this->event('stable-event');
        $eventChanged = $this->event('edited-event');
        $eventRemoved = $this->event('hidden-event');
        $sha = $this->baseline();

        $changed->update(['title' => 'Изменённое название', 'body' => '<p>Новый текст</p>']);
        $removed->update(['status' => 'draft']);
        $this->article('just-added');
        $eventChanged->update(['excerpt' => 'Исправленный анонс']);
        $eventRemoved->update(['status' => 'draft']);
        $this->event('new-event');
        $section->update(['title' => 'Другой раздел']);

        $admin = MoonshineUser::factory()->create();
        $report = app(MuseumPublicationDiff::class)->report($admin);
        $this->assertTrue($report['baseline_available']);
        $this->assertSame($sha, $report['baseline_sha256']);
        $this->assertSame('added', $this->findDiffRow($report, 'entries', 'news:just-added')['action']);
        $this->assertSame('removed', $this->findDiffRow($report, 'entries', 'news:removed')['action']);
        $this->assertSame('unchanged', $this->findDiffRow($report, 'entries', 'news:stable')['action']);
        $this->assertSame(['Основной текст', 'Название'],
            $this->findDiffRow($report, 'entries', 'news:changed')['changed_fields']);
        $this->assertSame('changed', $this->findDiffRow($report, 'events', 'edited-event')['action']);
        $this->assertSame('removed', $this->findDiffRow($report, 'events', 'hidden-event')['action']);
        $this->assertSame('added', $this->findDiffRow($report, 'events', 'new-event')['action']);
        $this->assertSame('unchanged', $this->findDiffRow($report, 'events', 'stable-event')['action']);
        $this->assertSame('changed', $this->findDiffRow($report, 'sections', 'one')['action']);
        $this->assertEqualsCanonicalizing(['added' => 2, 'removed' => 2, 'changed' => 3, 'unchanged' => 2], $report['summary']);
        $this->actingAs($admin, 'moonshine')->get(route('museum.content.compare'))->assertOk()
            ->assertSee('Изменённое название')->assertSee('Исчезнет из новой версии')
            ->assertSee('Добавится')->assertSee('Изменённые поля')
            ->assertHeader('Cache-Control', 'max-age=0, no-store, private')
            ->assertHeader('X-Robots-Tag', 'noindex, nofollow, noarchive');
        $this->assertSame($this->originalDataHash, hash_file('sha256', base_path('../web/src/data/published.json')));
        $this->assertSame(0, MuseumPublicationRun::count());
    }

    public function test_editor_scope_hides_other_sections_and_baseline_content(): void
    {
        $mine = MuseumSection::create(['slug' => 'my-section', 'title' => 'Доступно', 'status' => 'published']);
        $other = MuseumSection::create(['slug' => 'private-section', 'title' => 'Закрытый чужой', 'status' => 'published']);
        $myEntry = $this->article('shared-editable', section: $mine->id);
        $foreign = $this->article('sensitive-target', section: $other->id);
        $this->baseline();
        $foreign->update(['title' => 'ЧУЖОЙ СЕКРЕТ']);
        $myEntry->update(['title' => 'Своя новая публикация']);
        $role = MoonshineUserRole::query()->where('name', 'Editor')->firstOrFail();
        $editor = MoonshineUser::factory()->create(['moonshine_user_role_id' => $role->id]);
        $mine->editors()->attach($editor->id);
        $this->actingAs($editor, 'moonshine');
        $this->get(route('museum.content.compare'))->assertOk()
            ->assertSee('Своя новая публикация')->assertDontSee('ЧУЖОЙ СЕКРЕТ')
            ->assertDontSee('sensitive-target')->assertDontSee('Закрытый чужой');
        $report = app(MuseumPublicationDiff::class)->report($editor);
        $this->assertSame('assigned', $report['scope']);
        $this->assertCount(1, $report['groups']['entries']);
        $this->assertArrayNotHasKey('sections', $report['groups']);
    }

    public function test_tampered_missing_or_unmatched_baseline_fails_closed(): void
    {
        $this->article('first');
        $sha = $this->baseline();
        $admin = MoonshineUser::factory()->create();
        $root = $this->root.'/releases-root';
        file_put_contents($root.'/private-snapshots/'.$sha.'.json', 'tampered');
        $this->assertFalse(app(MuseumPublicationDiff::class)->report($admin)['baseline_available']);
        file_put_contents($root.'/private-snapshots/'.$sha.'.json', file_get_contents($this->root.'/baseline.json'));
        file_put_contents($root.'/current/snapshot-manifest.json', 'tampered');
        $this->assertFalse(app(MuseumPublicationDiff::class)->report($admin)['baseline_available']);
        $this->assertSame($this->originalDataHash, hash_file('sha256', base_path('../web/src/data/published.json')));
    }

    public function test_anonymous_user_cannot_access_comparison_or_trigger_export(): void
    {
        $this->article('private-test');
        $this->get(route('museum.content.compare'))->assertRedirect('/admin/login')
            ->assertDontSee('private-test');
        $this->assertSame(0, MuseumPublicationRun::count());
    }
}
