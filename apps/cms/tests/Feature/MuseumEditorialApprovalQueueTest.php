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
