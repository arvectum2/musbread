<?php

namespace Tests\Feature;

use App\Models\MuseumEntry;
use App\Models\MuseumEditorialReviewNote;
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

    public function test_retiring_url_inventory_includes_ru_en_and_events_without_guessing_redirects(): void
    {
        $old = $this->article('museum-history');
        $old->update(['title_en' => 'History', 'body_en' => '<p>English text</p>']);
        $event = $this->event('retired-festival');
        $this->baseline();
        $old->update(['status' => 'draft']);
        $event->update(['status' => 'draft']);

        $admin = MoonshineUser::factory()->create();
        $comparison = app(MuseumPublicationDiff::class)->report($admin);
        $paths = array_column($comparison['removed_urls'], 'path');
        $this->assertSame(['/en/news/museum-history/', '/events/retired-festival/',
            '/news/museum-history/'], $paths);
        $this->assertSame('en', $comparison['removed_urls'][0]['locale']);
        $this->assertSame('removed', $this->findDiffRow($comparison, 'entries', 'news:museum-history')['action']);
        $response = $this->actingAs($admin, 'moonshine')->get(route('museum.content.removed-urls'));
        $response->assertOk()->assertHeader('X-Robots-Tag', 'noindex, nofollow, noarchive')
            ->assertHeader('Cache-Control', 'max-age=0, no-store, private')
            ->assertHeader('Content-Type', 'text/csv; charset=UTF-8');
        $csv = $response->getContent();
        $this->assertStringStartsWith("\xEF\xBB\xBF", $csv);
        foreach ($paths as $path) $this->assertStringContainsString($path, $csv);
        $this->assertStringContainsString('Новый URL (согласовать)', $csv);
        $this->actingAs($admin, 'moonshine')->get(route('museum.content.compare'))->assertOk()
            ->assertSee('Адреса, которые требуют решения')
            ->assertSee('Скачать CSV для проверки перенаправлений');
        $this->assertSame(0, MuseumPublicationRun::count());
    }

    public function test_removed_url_csv_refuses_missing_baseline_and_guest(): void
    {
        $this->article('unpublished');
        $this->get(route('museum.content.removed-urls'))->assertRedirect('/admin/login');
        $admin = MoonshineUser::factory()->create();
        $this->actingAs($admin, 'moonshine')->get(route('museum.content.removed-urls'))
            ->assertStatus(409);
    }

    public function test_editor_csv_excludes_foreign_sections_and_sanitizes_spreadsheet_formulas(): void
    {
        $my = MuseumSection::create(['slug' => 'permitted-section', 'title' => 'Мой раздел', 'status' => 'published']);
        $foreign = MuseumSection::create(['slug' => 'private-section', 'title' => 'Скрытый раздел', 'status' => 'published']);
        $mine = $this->article('my-retiring', section: $my->id);
        $mine->update(['title' => '=HYPERLINK("https://malicious.invalid")']);
        $hidden = $this->article('hidden-retiring', section: $foreign->id);
        $this->baseline();
        $mine->update(['status' => 'draft']);
        $hidden->update(['status' => 'draft']);

        $role = MoonshineUserRole::query()->where('name', 'Editor')->firstOrFail();
        $editor = MoonshineUser::factory()->create(['moonshine_user_role_id' => $role->id]);
        $my->editors()->attach($editor->id);
        $this->actingAs($editor, 'moonshine');
        $csv = $this->get(route('museum.content.removed-urls'))->assertOk()->getContent();
        $this->assertStringContainsString('/news/my-retiring/', $csv);
        $this->assertStringNotContainsString('hidden-retiring', $csv);
        $this->assertStringNotContainsString('Скрытый раздел', $csv);
        $this->assertStringContainsString("'=HYPERLINK", $csv);
        $this->assertSame(1, count(app(MuseumPublicationDiff::class)->report($editor)['removed_urls']));
    }

    public function test_editorial_review_json_fingerprint_tracks_content_and_never_approves_it(): void
    {
        $old = $this->article('old-news');
        $this->baseline();
        $old->update(['status' => 'draft']);
        $new = $this->article('new-news');
        $admin = MoonshineUser::factory()->create();
        $this->actingAs($admin, 'moonshine');
        $response = $this->get(route('museum.content.release-review'))->assertOk()
            ->assertHeader('X-Robots-Tag', 'noindex, nofollow, noarchive')
            ->assertHeader('Cache-Control', 'max-age=0, no-store, private')
            ->assertHeader('Content-Disposition', 'attachment; filename="musbread-release-review.json"');
        $json = json_decode($response->getContent(), true, flags: JSON_THROW_ON_ERROR);
        $doc = $json['document'];
        $this->assertSame('musbread_editorial_review_only', $doc['kind']);
        $this->assertSame('verified_local_release_and_ephemeral_cms_export', $doc['source']);
        $this->assertSame(1, $doc['schema_version']);
        $this->assertSame('all', $doc['scope']);
        $this->assertEqualsCanonicalizing(['old-news', 'new-news'],
            array_map(static fn ($change) => substr($change['key'], 5), $doc['changes']['entries']));
        $this->assertSame('/news/old-news/', $doc['removed_urls'][0]['path']);
        $this->assertNull($doc['removed_urls'][0]['suggested_redirect']);
        $this->assertContains('not_a_museum_approval', $doc['limits']);
        $this->assertSame(hash('sha256', json_encode($doc, \App\Support\MuseumReleaseReviewPack::JSON_FLAGS)), $json['sha256']);
        $this->assertSame($this->originalDataHash, hash_file('sha256', base_path('../web/src/data/published.json')));
        $this->assertSame(0, MuseumPublicationRun::count());
        $this->get(route('museum.content.compare'))->assertOk()
            ->assertSee('Скачать единый JSON-пакет редакторской проверки');
        $new->update(['body' => '<p>Изменили содержимое после отчёта</p>']);
        $updated = json_decode($this->get(route('museum.content.release-review'))->assertOk()->getContent(), true);
        $this->assertNotSame($json['document']['candidate']['snapshot_sha256'],
            $updated['document']['candidate']['snapshot_sha256']);
    }

    public function test_editorial_review_json_handles_missing_baseline_without_false_changes(): void
    {
        $this->article('unapproved');
        $this->get(route('museum.content.release-review'))->assertRedirect('/admin/login');
        $admin = MoonshineUser::factory()->create();
        $this->actingAs($admin, 'moonshine')->get(route('museum.content.release-review'))
            ->assertStatus(409);
    }

    public function test_editorial_review_does_not_export_foreign_drafts_or_sections(): void
    {
        $mine = MuseumSection::create(['slug' => 'mine', 'title' => 'Мой раздел', 'status' => 'published']);
        $other = MuseumSection::create(['slug' => 'classified', 'title' => 'Чужой раздел', 'status' => 'published']);
        $ownEntry = $this->article('mine-news', section: $mine->id);
        $foreignEntry = $this->article('hidden-private', section: $other->id);
        $this->baseline();
        $ownEntry->update(['title' => 'Мой материал после изменений']);
        $foreignEntry->update(['title' => 'Секретные сведения <script>123</script>']);
        $role = MoonshineUserRole::query()->where('name', 'Editor')->firstOrFail();
        $editor = MoonshineUser::factory()->create(['moonshine_user_role_id' => $role->id]);
        $mine->editors()->attach($editor->id);
        $body = $this->actingAs($editor, 'moonshine')->get(route('museum.content.release-review'))
            ->assertOk()->getContent();
        $this->assertStringContainsString('mine-news', $body);
        $this->assertStringNotContainsString('hidden-private', $body);
        $this->assertStringNotContainsString('classified', $body);
        $this->assertStringNotContainsString('Секретные сведения', $body);
        $json = json_decode($body, true, flags: JSON_THROW_ON_ERROR);
        $this->assertSame('assigned', $json['document']['scope']);
        $this->assertArrayNotHasKey('sections', $json['document']['changes']);
        $this->assertSame(1, count($json['document']['changes']['entries']));
    }

    /** @return string */
    private function writeReviewPack(MoonshineUser $admin): string
    {
        $pack = app(\App\Support\MuseumReleaseReviewPack::class)->prepare($admin);
        $this->assertNotNull($pack);
        $file = $this->root.'/private-review.json';
        file_put_contents($file, json_encode($pack,
            \App\Support\MuseumReleaseReviewPack::JSON_FLAGS)."\n");
        return $file;
    }

    public function test_complete_review_package_verifies_and_can_gate_strict_export(): void
    {
        $this->article('ready-news');
        $this->event('ready-event');
        $this->baseline();
        $admin = MoonshineUser::factory()->create();
        $file = $this->root.'/downloaded-admin-review.json';
        $download = $this->actingAs($admin, 'moonshine')
            ->get(route('museum.content.release-review'))->assertOk();
        file_put_contents($file, $download->getContent());
        $verified = app(\App\Support\MuseumReviewPackVerifier::class)->verify($file);
        $this->assertTrue($verified['ok'], json_encode($verified));
        $this->assertSame('current', $verified['code']);
        $this->artisan('museum:verify-review', ['file' => $file])->assertSuccessful();
        $this->artisan('museum:verify-review', ['file' => $file, '--json' => true])->assertSuccessful();
        $output = $this->root.'/checked-export.json';
        $manifest = $this->root.'/checked-manifest.json';
        $this->artisan('museum:export', [
            '--review-pack' => $file, '--preflight-strict' => true,
            '--output' => $output, '--manifest' => $manifest,
            '--media-output-dir' => $this->root.'/checked-media',
            '--document-output-dir' => $this->root.'/checked-documents',
        ])->assertSuccessful();
        $data = json_decode(file_get_contents($output), true, flags: JSON_THROW_ON_ERROR);
        $this->assertSame('ready-news', $data['entries'][0]['slug']);
        $this->assertSame(0, MuseumPublicationRun::count());
        $this->assertSame($this->originalDataHash, hash_file('sha256', base_path('../web/src/data/published.json')));
    }

    public function test_intervening_edits_fail_verification_and_leave_export_files_untouched(): void
    {
        $entry = $this->article('earlier-version');
        $this->baseline();
        $admin = MoonshineUser::factory()->create();
        $file = $this->writeReviewPack($admin);
        $output = $this->root.'/protected-export.json';
        $manifest = $this->root.'/protected-manifest.json';
        file_put_contents($output, 'sentinel snapshot');
        file_put_contents($manifest, 'sentinel manifest');
        $entry->update(['body' => '<p>Правка внесена после рассмотрения</p>']);
        $result = app(\App\Support\MuseumReviewPackVerifier::class)->verify($file);
        $this->assertFalse($result['ok']);
        $this->assertSame('stale_review', $result['code']);
        $this->artisan('museum:verify-review', ['file' => $file])->assertFailed();
        $this->artisan('museum:export', [
            '--review-pack' => $file, '--output' => $output, '--manifest' => $manifest,
            '--media-output-dir' => $this->root.'/protected-media',
            '--document-output-dir' => $this->root.'/protected-documents',
        ])->assertFailed();
        $this->assertSame('sentinel snapshot', file_get_contents($output));
        $this->assertSame('sentinel manifest', file_get_contents($manifest));
        $this->assertDirectoryDoesNotExist($this->root.'/protected-media');
        $this->assertDirectoryDoesNotExist($this->root.'/protected-documents');
    }

    public function test_pack_tampering_and_editor_scope_are_rejected_even_if_checksum_is_recomputed(): void
    {
        $mine = MuseumSection::create(['slug' => 'permitted-review', 'title' => 'Свой раздел', 'status' => 'published']);
        $this->article('authorized', section: $mine->id);
        $this->baseline();
        $admin = MoonshineUser::factory()->create();
        $file = $this->writeReviewPack($admin);
        $json = json_decode(file_get_contents($file), true, flags: JSON_THROW_ON_ERROR);
        $json['document']['candidate']['snapshot_sha256'] = str_repeat('a', 64);
        file_put_contents($file, json_encode($json));
        $this->assertSame('checksum_mismatch', app(\App\Support\MuseumReviewPackVerifier::class)->verify($file)['code']);
        $json['sha256'] = hash('sha256', json_encode($json['document'],
            \App\Support\MuseumReleaseReviewPack::JSON_FLAGS));
        file_put_contents($file, json_encode($json));
        $this->assertSame('stale_review', app(\App\Support\MuseumReviewPackVerifier::class)->verify($file)['code']);

        $role = MoonshineUserRole::query()->where('name', 'Editor')->firstOrFail();
        $editor = MoonshineUser::factory()->create(['moonshine_user_role_id' => $role->id]);
        $mine->editors()->attach($editor->id);
        $editorPack = app(\App\Support\MuseumReleaseReviewPack::class)->prepare($editor);
        $this->assertNotNull($editorPack);
        file_put_contents($file, json_encode($editorPack));
        $this->assertSame('not_admin_report', app(\App\Support\MuseumReviewPackVerifier::class)->verify($file)['code']);
    }

    public function test_review_requires_verified_local_baseline_and_safe_file(): void
    {
        $this->article('source-item');
        $this->baseline();
        $admin = MoonshineUser::factory()->create();
        $file = $this->writeReviewPack($admin);
        $baseline = $this->root.'/releases-root/current';
        unlink($baseline);
        $this->assertSame('missing_baseline', app(\App\Support\MuseumReviewPackVerifier::class)->verify($file)['code']);
        $this->assertSame('invalid_file', app(\App\Support\MuseumReviewPackVerifier::class)->verify('https://example.invalid/file.json')['code']);
        $symlink = $this->root.'/review-link.json';
        symlink($file, $symlink);
        $this->assertSame('invalid_file', app(\App\Support\MuseumReviewPackVerifier::class)->verify($symlink)['code']);
        file_put_contents($file, '{not valid json');
        $this->assertSame('verification_failed', app(\App\Support\MuseumReviewPackVerifier::class)->verify($file)['code']);
    }

    public function test_critical_errors_cannot_be_accepted_using_matching_review(): void
    {
        $entry = $this->article('incomplete');
        $this->baseline();
        $admin = MoonshineUser::factory()->create();
        $entry->update(['body' => '<p>&nbsp;</p>']);
        $file = $this->writeReviewPack($admin);
        $result = app(\App\Support\MuseumReviewPackVerifier::class)->verify($file);
        $this->assertFalse($result['ok']);
        $this->assertSame('critical_issues', $result['code']);
        $this->artisan('museum:export', [
            '--review-pack' => $file, '--output' => $this->root.'/should-not-exist.json',
            '--manifest' => $this->root.'/should-not-exist-manifest.json',
        ])->assertFailed();
        $this->assertFileDoesNotExist($this->root.'/should-not-exist.json');
    }

    public function test_editor_without_grants_cannot_access_notes_and_admin_notes_are_version_bound(): void
    {
        $entry = $this->article('internal-review');
        $this->baseline();
        $entry->update(['title' => 'Изменённая версия']);
        $comparison = app(MuseumPublicationDiff::class)->report(MoonshineUser::factory()->create());
        $request = [
            'baseline_sha256' => $comparison['baseline_sha256'],
            'candidate_sha256' => $comparison['candidate_sha256'],
            'item_group' => 'entries', 'item_key' => 'news:internal-review',
            'decision' => 'needs_changes', 'note' => '<script>bad()</script> Исправить подпись',
        ];
        $this->get(route('museum.content.editorial-review'))->assertRedirect('/admin/login');
        $this->post(route('museum.content.editorial-review.store'), $request)->assertRedirect('/admin/login');
        $role = MoonshineUserRole::query()->where('name', 'Editor')->firstOrFail();
        $editor = MoonshineUser::factory()->create(['moonshine_user_role_id' => $role->id]);
        $this->actingAs($editor, 'moonshine');
        $this->get(route('museum.content.editorial-review'))->assertForbidden();
        $this->post(route('museum.content.editorial-review.store'), $request)->assertForbidden();
        $this->assertDatabaseCount('museum_editorial_review_notes', 0);
        $admin = MoonshineUser::factory()->create();
        $this->actingAs($admin, 'moonshine');
        $this->get(route('museum.content.compare'))->assertOk()->assertSee('Замечания и решения по версии');
        $this->get(route('museum.content.editorial-review'))->assertOk()
            ->assertSee('Изменённая версия')
            ->assertHeader('X-Robots-Tag', 'noindex, nofollow, noarchive')
            ->assertHeader('Cache-Control', 'max-age=0, no-store, private');
        $this->post(route('museum.content.editorial-review.store'), $request)->assertRedirect(route('museum.content.editorial-review'));
        $saved = MuseumEditorialReviewNote::query()->firstOrFail();
        $this->assertSame('needs_changes', $saved->decision);
        $this->assertSame($admin->id, $saved->actor_id);
        $this->assertSame($request['candidate_sha256'], $saved->candidate_sha256);
        $this->get(route('museum.content.editorial-review'))->assertOk()
            ->assertSee('&lt;script&gt;bad()&lt;/script&gt;', false)
            ->assertDontSee('<script>bad()</script>', false);
        $this->post(route('museum.content.editorial-review.store'), [
            ...$request, 'decision' => 'checked', 'note' => 'Проверено, требуется решение музея',
        ])->assertRedirect(route('museum.content.editorial-review'));
        $this->assertDatabaseCount('museum_editorial_review_notes', 2);
        $this->assertSame('needs_changes', $saved->fresh()->decision);
        $this->assertSame(0, MuseumPublicationRun::count());
    }

    public function test_editorial_note_rejects_stale_hashes_unknown_keys_and_bad_inputs(): void
    {
        $entry = $this->article('review-key');
        $this->baseline();
        $entry->update(['title' => 'Новый заголовок']);
        $admin = MoonshineUser::factory()->create();
        $this->actingAs($admin, 'moonshine');
        $report = app(MuseumPublicationDiff::class)->report($admin);
        $data = [
            'baseline_sha256' => $report['baseline_sha256'],
            'candidate_sha256' => $report['candidate_sha256'],
            'item_group' => 'entries', 'item_key' => 'news:review-key',
            'decision' => 'comment', 'note' => 'Проверить фотоматериал',
        ];
        $this->post(route('museum.content.editorial-review.store'), [
            ...$data, 'item_key' => 'news:unknown',
        ])->assertUnprocessable();
        $this->post(route('museum.content.editorial-review.store'), [
            ...$data, 'decision' => 'approved',
        ])->assertSessionHasErrors('decision');
        $this->post(route('museum.content.editorial-review.store'), [
            ...$data, 'note' => str_repeat('a', 1201),
        ])->assertSessionHasErrors('note');
        $entry->update(['title' => 'Ещё одна правка']);
        $this->post(route('museum.content.editorial-review.store'), $data)->assertStatus(409);
        $this->assertDatabaseCount('museum_editorial_review_notes', 0);
    }

    public function test_editorial_notes_do_not_carry_over_or_block_changed_snapshot(): void
    {
        $entry = $this->article('review-history');
        $this->baseline();
        $entry->update(['body' => 'Новая версия']);
        $admin = MoonshineUser::factory()->create();
        $this->actingAs($admin, 'moonshine');
        $report = app(MuseumPublicationDiff::class)->report($admin);
        $this->post(route('museum.content.editorial-review.store'), [
            'baseline_sha256' => $report['baseline_sha256'],
            'candidate_sha256' => $report['candidate_sha256'],
            'item_group' => 'entries', 'item_key' => 'news:review-history',
            'decision' => 'checked', 'note' => 'Проверено по старому макету',
        ])->assertRedirect();
        $entry->update(['body' => 'Совсем новый вариант']);
        $this->get(route('museum.content.editorial-review'))->assertOk()
            ->assertSee('Исторических замечаний к другим версиям: 1')
            ->assertDontSee('Проверено по старому макету');
        $this->assertDatabaseCount('museum_editorial_review_notes', 1);
    }

    public function test_granted_editor_can_review_only_currently_owned_entry_not_events_or_other_sections(): void
    {
        $mine = MuseumSection::create(['slug' => 'review-mine', 'title' => 'Своя рубрика', 'status' => 'published']);
        $foreign = MuseumSection::create(['slug' => 'review-foreign', 'title' => 'Чужая рубрика', 'status' => 'published']);
        $own = $this->article('mine-approval', section: $mine->id);
        $hidden = $this->article('classified-approval', section: $foreign->id);
        $event = $this->event('general-event-review');
        $this->baseline();
        $own->update(['title' => 'Доступный материал']);
        $hidden->update(['title' => 'Совершенно секретный материал']);
        $event->update(['title' => 'Секретная афиша']);
        $admin = MoonshineUser::factory()->create();
        $full = app(MuseumPublicationDiff::class)->report($admin);
        foreach (['mine-approval' => 'Примечание к своему', 'classified-approval' => 'Скрытая записка'] as $slug => $comment) {
            MuseumEditorialReviewNote::query()->create([
                'baseline_sha256' => $full['baseline_sha256'],
                'candidate_sha256' => $full['candidate_sha256'],
                'item_group' => 'entries', 'item_key' => 'news:'.$slug,
                'decision' => 'comment', 'note' => $comment,
                'actor_id' => $admin->id,
            ]);
        }
        MuseumEditorialReviewNote::query()->create([
            'baseline_sha256' => str_repeat('1', 64), 'candidate_sha256' => str_repeat('2', 64),
            'item_group' => 'entries', 'item_key' => 'news:classified-approval',
            'decision' => 'comment', 'note' => 'Старая секретная записка', 'actor_id' => $admin->id,
        ]);
        $role = MoonshineUserRole::query()->where('name', 'Editor')->firstOrFail();
        $editor = MoonshineUser::factory()->create(['moonshine_user_role_id' => $role->id]);
        $mine->editors()->attach($editor->id);
        $this->actingAs($editor, 'moonshine');
        $this->get(route('museum.content.compare'))->assertOk()
            ->assertSee('Замечания и решения по версии');
        $this->get(route('museum.content.editorial-review'))->assertOk()
            ->assertSeeText('Есть замечания: 1')
            ->assertSeeText('Требуются исправления: 0')
            ->assertSee('Доступный материал')->assertSee('Примечание к своему')
            ->assertDontSee('classified-approval')->assertDontSee('Совершенно секретный материал')
            ->assertDontSee('Скрытая записка')->assertDontSee('Старая секретная записка')
            ->assertDontSee('Секретная афиша')->assertDontSee('review-foreign')
            ->assertDontSee('Исторических замечаний к другим версиям');
        $payload = [
            'baseline_sha256' => $full['baseline_sha256'],
            'candidate_sha256' => $full['candidate_sha256'],
            'item_group' => 'entries', 'item_key' => 'news:mine-approval',
            'decision' => 'needs_changes', 'note' => 'Уточнить подпись в своём разделе',
        ];
        $this->post(route('museum.content.editorial-review.store'), $payload)
            ->assertRedirect(route('museum.content.editorial-review'));
        $this->assertDatabaseHas('museum_editorial_review_notes', [
            'item_key' => 'news:mine-approval', 'actor_id' => $editor->id,
            'note' => 'Уточнить подпись в своём разделе',
        ]);
        $this->post(route('museum.content.editorial-review.store'), [
            ...$payload, 'item_key' => 'news:classified-approval',
        ])->assertUnprocessable();
        $this->post(route('museum.content.editorial-review.store'), [
            ...$payload, 'item_group' => 'events', 'item_key' => 'general-event-review',
        ])->assertUnprocessable();
        $this->post(route('museum.content.editorial-review.store'), [
            ...$payload, 'item_group' => 'sections', 'item_key' => 'review-mine',
        ])->assertUnprocessable();
        $this->assertDatabaseCount('museum_editorial_review_notes', 4);
        $this->assertSame(0, MuseumPublicationRun::count());
    }

    public function test_revocation_and_cross_section_move_prevent_old_editor_reviews(): void
    {
        $mine = MuseumSection::create(['slug' => 'revoked-mine', 'title' => 'Разрешено', 'status' => 'published']);
        $foreign = MuseumSection::create(['slug' => 'revoked-other', 'title' => 'Запрещено', 'status' => 'published']);
        $moving = $this->article('moving-away', section: $mine->id);
        $still = $this->article('still-mine', section: $mine->id);
        $this->baseline();
        $moving->update(['museum_section_id' => $foreign->id, 'title' => 'Передан другому редактору']);
        $still->update(['title' => 'Оставшийся материал']);
        $admin = MoonshineUser::factory()->create();
        $full = app(MuseumPublicationDiff::class)->report($admin);
        $role = MoonshineUserRole::query()->where('name', 'Editor')->firstOrFail();
        $editor = MoonshineUser::factory()->create(['moonshine_user_role_id' => $role->id]);
        $mine->editors()->attach($editor->id);
        $this->actingAs($editor, 'moonshine');
        $this->get(route('museum.content.editorial-review'))->assertOk()
            ->assertSee('Оставшийся материал')
            ->assertDontSee('Передан другому редактору')->assertDontSee('moving-away');
        $payload = [
            'baseline_sha256' => $full['baseline_sha256'],
            'candidate_sha256' => $full['candidate_sha256'],
            'item_group' => 'entries', 'item_key' => 'news:moving-away',
            'decision' => 'checked', 'note' => 'Попытка отметить чужой материал',
        ];
        $this->post(route('museum.content.editorial-review.store'), $payload)
            ->assertUnprocessable();
        $mine->editors()->detach($editor->id);
        $this->get(route('museum.content.editorial-review'))->assertForbidden();
        $this->post(route('museum.content.editorial-review.store'), [
            ...$payload, 'item_key' => 'news:still-mine',
        ])->assertForbidden();
        $this->assertDatabaseCount('museum_editorial_review_notes', 0);
    }

    public function test_admin_still_reviews_events_and_structure_without_section_grants(): void
    {
        $section = MuseumSection::create(['slug' => 'admin-structure', 'title' => 'Музейная структура', 'status' => 'published']);
        $this->article('admin-review-page', section: $section->id);
        $event = $this->event('admin-event-review');
        $this->baseline();
        $event->update(['title' => 'Обновлённая афиша']);
        $section->update(['title' => 'Обновлённая структура']);
        $admin = MoonshineUser::factory()->create();
        $report = app(MuseumPublicationDiff::class)->report($admin);
        $this->actingAs($admin, 'moonshine');
        $this->get(route('museum.content.editorial-review'))->assertOk()
            ->assertSee('Обновлённая афиша')->assertSee('Обновлённая структура');
        foreach ([['events', 'admin-event-review'], ['sections', 'admin-structure']] as [$group, $key]) {
            $this->post(route('museum.content.editorial-review.store'), [
                'baseline_sha256' => $report['baseline_sha256'],
                'candidate_sha256' => $report['candidate_sha256'],
                'item_group' => $group, 'item_key' => $key,
                'decision' => 'comment', 'note' => 'Проверка администратором',
            ])->assertRedirect(route('museum.content.editorial-review'));
        }
        $this->assertDatabaseCount('museum_editorial_review_notes', 2);
    }

    public function test_summary_tracks_latest_internal_decision_and_resets_after_new_snapshot(): void
    {
        $first = $this->article('first-needs');
        $second = $this->article('second-awaiting');
        $this->baseline();
        $first->update(['title' => 'Первая новая редакция']);
        $second->update(['title' => 'Вторая новая редакция']);
        $admin = MoonshineUser::factory()->create();
        $this->actingAs($admin, 'moonshine');
        $report = app(MuseumPublicationDiff::class)->report($admin);
        $request = [
            'baseline_sha256' => $report['baseline_sha256'],
            'candidate_sha256' => $report['candidate_sha256'],
            'item_group' => 'entries', 'item_key' => 'news:first-needs',
            'decision' => 'needs_changes', 'note' => 'Исправить материал',
        ];
        $this->get(route('museum.content.editorial-review'))->assertOk()
            ->assertSeeText('Ещё не рассмотрено: 2')
            ->assertSeeText('Требуются исправления: 0');
        $this->post(route('museum.content.editorial-review.store'), $request)->assertRedirect();
        $this->get(route('museum.content.editorial-review'))->assertOk()
            ->assertSeeText('Требуются исправления: 1')
            ->assertSeeText('Ещё не рассмотрено: 1')
            ->assertSee('href="#review-', false);
        $this->post(route('museum.content.editorial-review.store'), [
            ...$request, 'decision' => 'checked', 'note' => 'Перепроверено в команде',
        ])->assertRedirect();
        $this->get(route('museum.content.editorial-review'))->assertOk()
            ->assertSeeText('Требуются исправления: 0')
            ->assertSeeText('Проверено внутри команды: 1')
            ->assertSeeText('Ещё не рассмотрено: 1');
        $this->post(route('museum.content.editorial-review.store'), [
            ...$request, 'note' => 'Найдено новое замечание',
        ])->assertRedirect();
        $this->get(route('museum.content.editorial-review'))->assertOk()
            ->assertSeeText('Требуются исправления: 1')
            ->assertSeeText('Проверено внутри команды: 0');
        $second->update(['title' => 'Третья редакция']);
        $this->get(route('museum.content.editorial-review'))->assertOk()
            ->assertSeeText('Требуются исправления: 0')
            ->assertSeeText('Ещё не рассмотрено: 2')
            ->assertSee('Исторических замечаний к другим версиям: 3');
        $this->assertSame(0, MuseumPublicationRun::count());
    }

    public function test_anonymous_user_cannot_access_comparison_or_trigger_export(): void
    {
        $this->article('private-test');
        $this->get(route('museum.content.compare'))->assertRedirect('/admin/login')
            ->assertDontSee('private-test');
        $this->assertSame(0, MuseumPublicationRun::count());
    }
}
