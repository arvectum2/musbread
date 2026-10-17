<?php

namespace Tests\Feature;

use App\Jobs\PublishMuseumSnapshot;
use App\Models\MuseumContentApproval;
use App\Models\MuseumEntry;
use App\Models\MuseumPublicationRun;
use App\Support\MuseumApprovalRevision;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Queue;
use Illuminate\Support\Facades\Artisan;
use MoonShine\Laravel\Models\MoonshineUser;
use MoonShine\Laravel\Models\MoonshineUserRole;
use Tests\TestCase;

class MuseumEditorialApprovalQueueTest extends TestCase
{
    use RefreshDatabase;

    private function allowOptIn(): void
    {
        config([
            'museum.editorial_approval_queue' => true,
            'museum.queue_publication' => true,
            'queue.default' => 'database',
            'cache.default' => 'database',
        ]);
        Queue::fake();
    }

    private function entry(string $slug = 'approved-news', string $status = 'published'): MuseumEntry
    {
        return MuseumEntry::create([
            'type' => 'news',
            'slug' => $slug,
            'title' => 'Проверка одобрения',
            'body' => '<p>Подтверждённое содержимое теста</p>',
            'status' => $status,
        ]);
    }

    protected function tearDown(): void
    {
        config(['museum.editorial_approval_queue' => false,
                'museum.queue_publication' => false]);
        parent::tearDown();
    }

    public function test_explicit_admin_approval_timestamps_once_and_dispatches_private_queue_once(): void
    {
        $this->allowOptIn();
        $user = MoonshineUser::factory()->create();
        $entry = $this->entry();
        $this->actingAs($user, 'moonshine');

        $hash = MuseumApprovalRevision::fingerprint($entry->fresh());
        $this->get(route('museum.content.preflight'))->assertOk()
            ->assertSee('Одобрить эту редакцию и запросить закрытую выгрузку')
            ->assertSee($hash)
            ->assertSee('name="_token"', false);

        $clockStart = now()->subSecond();
        $request = route('museum.entries.approve-and-queue', $entry);
        $this->post($request, ['revision_sha256' => $hash])
            ->assertRedirect(route('museum.content.preflight'))
            ->assertSessionHas('museum_export_queue_result');
        $this->assertDatabaseCount('museum_content_approvals', 1);
        $this->assertDatabaseCount('museum_publication_runs', 1);
        $record = MuseumContentApproval::sole();
        $this->assertSame($user->id, $record->actor_id);
        $this->assertSame($entry->id, $record->museum_entry_id);
        $this->assertSame($hash, $record->revision_sha256);
        $this->assertSame('queued', $record->dispatch_status);
        $this->assertTrue($record->approved_at->greaterThanOrEqualTo($clockStart));
        $this->assertNotNull($record->publication_run_id);
        Queue::assertPushed(PublishMuseumSnapshot::class, 1);
        $this->get(route('museum.content.approval-journal'))->assertOk()
            ->assertSee($hash)
            ->assertSee('не является')
            ->assertHeader('Cache-Control', 'max-age=0, no-store, private')
            ->assertHeader('X-Robots-Tag', 'noindex, nofollow, noarchive');

        // Replaying identical approval is idempotent and preserves the actual time.
        $first = $record->approved_at->toISOString();
        $this->post($request, ['revision_sha256' => $hash])
            ->assertRedirect(route('museum.content.preflight'));
        $this->assertSame($first, MuseumContentApproval::sole()->approved_at->toISOString());
        $this->assertDatabaseCount('museum_content_approvals', 1);
        $this->assertDatabaseCount('museum_publication_runs', 1);
        Queue::assertPushed(PublishMuseumSnapshot::class, 1);

        // Body change changes fingerprint; old signed form cannot approve.
        $entry->update(['body' => '<p>Другая редакция</p>']);
        $this->post($request, ['revision_sha256' => $hash])->assertStatus(409);
        $this->assertDatabaseCount('museum_content_approvals', 1);
        $nextHash = MuseumApprovalRevision::fingerprint($entry->fresh());
        $this->assertNotSame($hash, $nextHash);
        $this->post($request, ['revision_sha256' => $nextHash])
            ->assertRedirect(route('museum.content.preflight'));
        $this->assertDatabaseCount('museum_content_approvals', 2);
        $this->assertSame(1, MuseumPublicationRun::count()); // active export coalesces requests
        Queue::assertPushed(PublishMuseumSnapshot::class, 1);
    }

    public function test_guest_editor_and_disabled_mode_are_denied_without_approval(): void
    {
        $entry = $this->entry();
        $hash = MuseumApprovalRevision::fingerprint($entry->fresh());
        $route = route('museum.entries.approve-and-queue', $entry);
        $this->post($route, ['revision_sha256' => $hash])->assertRedirect('/admin/login');

        $this->allowOptIn();
        $role = MoonshineUserRole::where('name', 'Editor')->firstOrFail();
        $editor = MoonshineUser::factory()->create(['moonshine_user_role_id' => $role->id]);
        $this->actingAs($editor, 'moonshine');
        $this->post($route, ['revision_sha256' => $hash])->assertForbidden();
        $this->get(route('museum.content.approval-journal'))->assertForbidden();
        $this->get(route('museum.content.preflight'))->assertOk()
            ->assertDontSee('Одобрить эту редакцию и запросить закрытую выгрузку');

        $this->actingAs(MoonshineUser::factory()->create(), 'moonshine');
        config(['museum.editorial_approval_queue' => false]);
        $this->post($route, ['revision_sha256' => $hash])->assertStatus(409);
        config(['museum.editorial_approval_queue' => true, 'cache.default' => 'array']);
        $this->post($route, ['revision_sha256' => $hash])->assertStatus(409);
        config(['cache.default' => 'database', 'queue.default' => 'sync']);
        $this->post($route, ['revision_sha256' => $hash])->assertStatus(409);
        Queue::assertNothingPushed();
        $this->assertDatabaseCount('museum_content_approvals', 0);
    }

    public function test_scheduled_draft_expired_or_unready_content_never_approves(): void
    {
        $this->allowOptIn();
        $this->actingAs(MoonshineUser::factory()->create(), 'moonshine');

        $draft = $this->entry('not-ready-draft', 'draft');
        $future = $this->entry('not-ready-future');
        $future->update(['published_at' => now()->addDay()]);
        $expired = $this->entry('not-ready-expired');
        $expired->update(['unpublish_at' => now()->subMinute()]);
        $valid = $this->entry('bad-broken-link');
        $valid->update(['body' => '<p><a href="/news/never-created/">Broken link</a></p>']);

        foreach ([$draft, $future, $expired, $valid] as $entry) {
            $route = route('museum.entries.approve-and-queue', $entry);
            $this->post($route, ['revision_sha256' => MuseumApprovalRevision::fingerprint($entry->fresh())])
                ->assertStatus(422);
        }
        Queue::assertNothingPushed();
        $this->assertDatabaseCount('museum_content_approvals', 0);
    }

    public function test_invalid_fingerprint_and_draft_edits_never_create_an_approval(): void
    {
        $this->allowOptIn();
        $this->actingAs(MoonshineUser::factory()->create(), 'moonshine');
        $entry = $this->entry();
        $route = route('museum.entries.approve-and-queue', $entry);
        $this->post($route, ['revision_sha256' => 'anything'])->assertSessionHasErrors('revision_sha256');
        $expected = MuseumApprovalRevision::fingerprint($entry);
        $entry->update(['seo_title' => 'SEO changed, not same revision']);
        $this->post($route, ['revision_sha256' => $expected])->assertStatus(409);
        $this->assertDatabaseCount('museum_content_approvals', 0);
        Queue::assertNothingPushed();
    }

    public function test_queue_failure_keeps_original_approval_time_for_recovery(): void
    {
        $this->allowOptIn();
        $this->actingAs(MoonshineUser::factory()->create(), 'moonshine');
        $entry = $this->entry('dispatch-failure');
        $original = MuseumApprovalRevision::fingerprint($entry->fresh());
        Artisan::shouldReceive('call')->once()->with('museum:queue-export')->andReturn(1);
        $this->post(route('museum.entries.approve-and-queue', $entry), [
            'revision_sha256' => $original,
        ])->assertStatus(503);
        $this->assertDatabaseCount('museum_content_approvals', 1);
        $record = MuseumContentApproval::sole();
        $this->assertSame('failed', $record->dispatch_status);
        $this->assertSame($original, $record->revision_sha256);
        $this->assertNotNull($record->approved_at);
        $this->assertNull($record->publication_run_id);
    }

    public function test_opt_in_export_fails_closed_before_writing_any_output_and_rechecks_revisions(): void
    {
        $this->allowOptIn();
        $entry = $this->entry('gate-entry');
        $dir = storage_path('framework/testing/approval-gate');
        if (! is_dir($dir)) mkdir($dir, 0755, true);
        $out = $dir.'/data.json';
        $manifest = $dir.'/manifest.json';
        file_put_contents($out, 'previous-approved-release');
        file_put_contents($manifest, 'previous-approved-manifest');
        $args = ['--output' => $out, '--manifest' => $manifest,
            '--media-output-dir' => $dir.'/media', '--document-output-dir' => $dir.'/documents'];
        try {
            $this->assertSame(1, Artisan::call('museum:export', $args));
            $this->assertSame('previous-approved-release', file_get_contents($out));
            $this->assertSame('previous-approved-manifest', file_get_contents($manifest));
            $this->assertDirectoryDoesNotExist($dir.'/media');

            $hash = MuseumApprovalRevision::fingerprint($entry->fresh());
            MuseumContentApproval::create(['museum_entry_id' => $entry->id,
                'actor_id' => 1, 'revision_sha256' => $hash,
                'approved_at' => now('UTC'), 'dispatch_status' => 'queued']);
            $this->assertSame(0, Artisan::call('museum:export', $args));
            $this->assertSame(['gate-entry'],
                array_column(json_decode(file_get_contents($out), true)['entries'], 'slug'));

            $approvedOutput = file_get_contents($out);
            $approvedManifest = file_get_contents($manifest);
            $entry->update(['body' => '<p>Содержимое изменилось после одобрения.</p>']);
            $this->assertSame(1, Artisan::call('museum:export', $args));
            $this->assertSame($approvedOutput, file_get_contents($out));
            $this->assertSame($approvedManifest, file_get_contents($manifest));
            $this->assertDatabaseCount('museum_content_approvals', 1);

            $entry->update(['status' => 'draft']);
            // Withdrawing material without publishing new content cannot leak
            // the now-draft entry; an empty export is permissible in isolation.
            $this->assertSame(0, Artisan::call('museum:export', $args));
            $this->assertSame([], json_decode(file_get_contents($out), true)['entries']);
        } finally {
            @unlink($out);
            @unlink($manifest);
        }
    }

    public function test_opt_in_export_refuses_uncovered_content_types_instead_of_bypassing_approval(): void
    {
        $this->allowOptIn();
        $dir = storage_path('framework/testing/approval-uncovered');
        if (! is_dir($dir)) mkdir($dir, 0755, true);
        $out = $dir.'/data.json';
        $manifest = $dir.'/manifest.json';
        file_put_contents($out, 'previous-release');
        $section = \App\Models\MuseumSection::create([
            'slug' => 'published-section', 'title' => 'Тестовый раздел', 'status' => 'published',
        ]);
        try {
            $this->assertSame(1, Artisan::call('museum:export', [
                '--output' => $out, '--manifest' => $manifest,
                '--media-output-dir' => $dir.'/media',
                '--document-output-dir' => $dir.'/documents',
            ]));
            $this->assertSame('previous-release', file_get_contents($out));
            $this->assertFileDoesNotExist($manifest);
            $section->update(['status' => 'draft']);
            config(['museum.queue_publication' => false]);
            $this->assertSame(1, Artisan::call('museum:export', [
                '--output' => $out, '--manifest' => $manifest,
                '--media-output-dir' => $dir.'/media',
                '--document-output-dir' => $dir.'/documents',
            ]));
            $this->assertSame('previous-release', file_get_contents($out));
        } finally {
            @unlink($out);
            @unlink($manifest);
        }
    }

    public function test_attachment_description_and_document_label_invalidate_prior_approval(): void
    {
        $this->allowOptIn();
        $entry = $this->entry('asset-fingerprint');
        $media = \App\Models\MuseumMedia::create([
            'museum_entry_id' => $entry->id,
            'storage_path' => 'museum/media/test-fingerprint.webp',
            'sha256' => str_repeat('a', 64),
            'alt' => 'Тестовый макет страницы музея с текстовой подписью',
            'caption' => 'Подпись перед одобрением',
            'long_description' => 'Подробное описание до одобрения',
            'width' => 100, 'height' => 100, 'size_bytes' => 100,
        ]);
        $document = \App\Models\MuseumDocument::create([
            'museum_entry_id' => $entry->id,
            'label' => 'Правила тестового посещения',
            'file_type' => 'pdf', 'storage_path' => 'museum/documents/test-fingerprint.pdf',
            'sha256' => str_repeat('b', 64), 'size_bytes' => 100,
        ]);
        $approvedHash = MuseumApprovalRevision::fingerprint($entry->fresh());
        MuseumContentApproval::create([
            'museum_entry_id' => $entry->id, 'actor_id' => 1,
            'revision_sha256' => $approvedHash,
            'approved_at' => now('UTC'), 'dispatch_status' => 'queued',
        ]);
        app(\App\Support\MuseumExplicitApprovalGate::class)->assertApproved();
        $media->update(['long_description' => 'Новый текст с другими фактами о предмете']);
        $mediaHash = MuseumApprovalRevision::fingerprint($entry->fresh());
        $this->assertNotSame($approvedHash, $mediaHash);
        $document->update(['label' => 'Пересмотренные правила тестового посещения']);
        $this->assertNotSame($mediaHash, MuseumApprovalRevision::fingerprint($entry->fresh()));
        $this->expectException(\RuntimeException::class);
        $this->expectExceptionMessage('Unapproved public entry');
        app(\App\Support\MuseumExplicitApprovalGate::class)->assertApproved();
    }

    public function test_admin_can_approve_section_and_event_and_export_one_consistent_set(): void
    {
        $this->allowOptIn();
        $this->actingAs(MoonshineUser::factory()->create(), 'moonshine');
        $section = \App\Models\MuseumSection::create([
            'slug' => 'bakery', 'title' => 'Тестовый раздел', 'status' => 'published',
        ]);
        $event = \App\Models\MuseumEvent::create([
            'slug' => 'bread-week', 'title' => 'Тестовое событие',
            'category' => 'Афиша', 'starts_at' => '2026-12-15',
            'body' => '<p>Встреча с сотрудниками музея</p>',
            'excerpt' => 'Программа тестового события',
            'status' => 'published', 'museum_section_id' => $section->id,
        ]);
        $entry = $this->entry('section-news');
        $entry->update(['museum_section_id' => $section->id]);

        $before = $this->get(route('museum.content.preflight'))->assertOk();
        $before->assertSee('Одобрить структуру раздела')
            ->assertSee('Одобрить редакцию события')
            ->assertSee('Одобрить эту редакцию');
        $this->post(route('museum.sections.approve-and-queue', $section), [
            'revision_sha256' => MuseumApprovalRevision::forSubject($section->fresh()),
        ])->assertRedirect(route('museum.content.preflight'));
        $this->post(route('museum.events.approve-and-queue', $event), [
            'revision_sha256' => MuseumApprovalRevision::forSubject($event->fresh()),
        ])->assertRedirect(route('museum.content.preflight'));
        $this->post(route('museum.entries.approve-and-queue', $entry), [
            'revision_sha256' => MuseumApprovalRevision::fingerprint($entry->fresh()),
        ])->assertRedirect(route('museum.content.preflight'));

        $this->assertDatabaseCount('museum_content_approvals', 3);
        $this->assertSame(['museum_entry_id', 'museum_event_id', 'museum_section_id'],
            collect(MuseumContentApproval::all())->flatMap(
                fn ($row) => collect(['museum_event_id','museum_entry_id','museum_section_id'])
                    ->filter(fn ($key) => $row->$key !== null)
            )->values()->sort()->values()->all());
        // The same active release request coalesces all three approvals.
        $this->assertSame(1, MuseumPublicationRun::count());
        Queue::assertPushed(PublishMuseumSnapshot::class, 1);

        $dir = storage_path('framework/testing/multi-subject-export');
        if (! is_dir($dir)) mkdir($dir, 0700, true);
        $json = $dir.'/data.json';
        $manifest = $dir.'/manifest.json';
        try {
            $this->assertSame(0, Artisan::call('museum:export', [
                '--output' => $json, '--manifest' => $manifest,
                '--media-output-dir' => $dir.'/media',
                '--document-output-dir' => $dir.'/documents',
                '--preflight-strict' => true,
            ]));
            $payload = json_decode(file_get_contents($json), true);
            $this->assertSame(['bakery'], array_column($payload['sections'], 'slug'));
            $this->assertSame(['bread-week'], array_column($payload['events'], 'slug'));
            $this->assertSame(['section-news'], array_column($payload['entries'], 'slug'));
            $this->get(route('museum.content.approval-journal'))->assertOk()
                ->assertSee('Событие #'.$event->id)
                ->assertSee('Раздел #'.$section->id);
            // The same multi-subject approval gate must also work inside the
            // queued worker, not only when invoking the exporter manually.
            (new PublishMuseumSnapshot(MuseumPublicationRun::sole()->id,
                $dir.'/worker.json', $dir.'/worker-manifest.json', $dir.'/worker-media'))->handle();
            $this->assertSame('succeeded', MuseumPublicationRun::sole()->status);
            $workerPayload = json_decode(file_get_contents($dir.'/worker.json'), true);
            $this->assertSame(['bread-week'], array_column($workerPayload['events'], 'slug'));
            $this->assertSame(['bakery'], array_column($workerPayload['sections'], 'slug'));
            $this->assertSame(['section-news'], array_column($workerPayload['entries'], 'slug'));
            $oldContent = file_get_contents($json);
            $oldManifest = file_get_contents($manifest);
            $event->update(['excerpt' => 'Изменённый анонс события']);
            $this->assertSame(1, Artisan::call('museum:export', [
                '--output' => $json, '--manifest' => $manifest,
                '--media-output-dir' => $dir.'/media',
                '--document-output-dir' => $dir.'/documents',
            ]));
            $this->assertSame($oldContent, file_get_contents($json));
            $this->assertSame($oldManifest, file_get_contents($manifest));
            $event->update(['excerpt' => 'Программа тестового события']);
            $section->update(['title' => 'Изменённый заголовок раздела']);
            $this->assertSame(1, Artisan::call('museum:export', [
                '--output' => $json, '--manifest' => $manifest,
                '--media-output-dir' => $dir.'/media',
                '--document-output-dir' => $dir.'/documents',
            ]));
            $this->assertSame($oldContent, file_get_contents($json));
        } finally {
            @unlink($json);
            @unlink($manifest);
            @unlink($dir.'/worker.json');
            @unlink($dir.'/worker-manifest.json');
        }
    }

    public function test_unapproved_event_section_drafts_and_stale_signatures_are_rejected(): void
    {
        $this->allowOptIn();
        $this->actingAs(MoonshineUser::factory()->create(), 'moonshine');
        $section = \App\Models\MuseumSection::create([
            'slug' => 'draft-parent', 'title' => 'Закрытый родитель', 'status' => 'draft',
        ]);
        $child = \App\Models\MuseumSection::create([
            'slug' => 'hidden-child', 'title' => 'Вложенный раздел',
            'status' => 'published', 'parent_id' => $section->id,
        ]);
        $event = \App\Models\MuseumEvent::create([
            'slug' => 'private-event', 'title' => 'Тестовое событие', 'category' => 'Афиша',
            'starts_at' => '2026-12-15', 'excerpt' => 'Анонс',
            'body' => '<p>Описание</p>', 'status' => 'draft',
        ]);

        $this->post(route('museum.sections.approve-and-queue', $child), [
            'revision_sha256' => MuseumApprovalRevision::forSubject($child->fresh()),
        ])->assertStatus(422);
        $this->post(route('museum.events.approve-and-queue', $event), [
            'revision_sha256' => MuseumApprovalRevision::forSubject($event->fresh()),
        ])->assertStatus(422);
        $event->update(['status' => 'published']);
        $oldHash = MuseumApprovalRevision::forSubject($event->fresh());
        $event->update(['seo_title' => 'Правка после предпросмотра']);
        $this->post(route('museum.events.approve-and-queue', $event), [
            'revision_sha256' => $oldHash,
        ])->assertStatus(409);
        $this->assertDatabaseCount('museum_content_approvals', 0);
        Queue::assertNothingPushed();

        $editorRole = MoonshineUserRole::where('name', 'Editor')->firstOrFail();
        $editor = MoonshineUser::factory()->create(['moonshine_user_role_id' => $editorRole->id]);
        $this->actingAs($editor, 'moonshine');
        $this->post(route('museum.events.approve-and-queue', $event), [
            'revision_sha256' => MuseumApprovalRevision::forSubject($event->fresh()),
        ])->assertForbidden();
        $this->post(route('museum.sections.approve-and-queue', $child), [
            'revision_sha256' => MuseumApprovalRevision::forSubject($child->fresh()),
        ])->assertForbidden();
    }

    public function test_changing_between_two_approved_versions_invalidates_in_flight_capture(): void
    {
        $this->allowOptIn();
        $entry = $this->entry('snapshot-version');
        $first = MuseumApprovalRevision::fingerprint($entry->fresh());
        MuseumContentApproval::create([
            'museum_entry_id' => $entry->id, 'actor_id' => 1,
            'revision_sha256' => $first, 'approved_at' => now('UTC'),
            'dispatch_status' => 'queued',
        ]);
        $gate = app(\App\Support\MuseumExplicitApprovalGate::class);
        $captured = $gate->capture();
        $entry->update(['body' => '<p>Следующая подтверждённая редакция</p>']);
        $newHash = MuseumApprovalRevision::fingerprint($entry->fresh());
        MuseumContentApproval::create([
            'museum_entry_id' => $entry->id, 'actor_id' => 1,
            'revision_sha256' => $newHash, 'approved_at' => now('UTC'),
            'dispatch_status' => 'queued',
        ]);
        $this->assertNotSame($captured, $gate->capture());
        $this->expectException(\RuntimeException::class);
        $this->expectExceptionMessage('Approved publication set changed');
        $gate->assertUnchanged($captured);
    }

    public function test_published_status_by_itself_is_not_an_approval_event(): void
    {
        $this->allowOptIn();
        $entry = $this->entry('save-is-not-approval', 'draft');
        $entry->update(['status' => 'published']);
        $entry->update(['body' => '<p>Обычное редактирование после сохранения</p>']);
        $this->assertDatabaseCount('museum_content_approvals', 0);
        $this->assertDatabaseCount('museum_publication_runs', 0);
        Queue::assertNothingPushed();
    }

}
