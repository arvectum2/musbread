<?php

namespace Tests\Feature;

use App\Jobs\PublishMuseumSnapshot;
use App\Models\MuseumContentApproval;
use App\Models\MuseumEntry;
use App\Models\MuseumPublicationRun;
use App\Models\MuseumSection;
use App\Support\MuseumApprovalRevision;
use Illuminate\Auth\Access\AuthorizationException;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Queue;
use MoonShine\Laravel\Models\MoonshineUser;
use MoonShine\Laravel\Models\MoonshineUserRole;
use Tests\TestCase;

/** Repeated interleaved editor actions in a SHARED test database.
 * Not a simultaneous multi-process database stress / network benchmark.
 */
final class MuseumInterleavedEditorialLoadTest extends TestCase
{
    use RefreshDatabase;

    public function test_two_editors_interleave_updates_without_cross_section_leak_or_stale_approval(): void
    {
        config([
            'museum.editorial_approval_queue' => true,
            'museum.queue_publication' => true,
            'queue.default' => 'database',
            'cache.default' => 'database',
        ]);
        Queue::fake();

        $left = MuseumSection::create([
            'slug' => 'load-gallery-left', 'title' => 'Левый раздел',
            'status' => 'published',
        ]);
        $right = MuseumSection::create([
            'slug' => 'load-gallery-right', 'title' => 'Правый раздел',
            'status' => 'published',
        ]);
        $role = MoonshineUserRole::where('name', 'Editor')->firstOrFail();
        $editorA = MoonshineUser::factory()->create(['moonshine_user_role_id' => $role->id]);
        $editorB = MoonshineUser::factory()->create(['moonshine_user_role_id' => $role->id]);
        $admin = MoonshineUser::factory()->create();
        $left->editors()->attach($editorA->id);
        $right->editors()->attach($editorB->id);

        $a = MuseumEntry::create([
            'type' => 'news', 'slug' => 'load-news-a',
            'title' => 'Музейная новость А',
            'body' => '<p>Проверенный текст А</p>', 'status' => 'published',
            'museum_section_id' => $left->id,
        ]);
        $b = MuseumEntry::create([
            'type' => 'news', 'slug' => 'load-news-b',
            'title' => 'Музейная новость Б',
            'body' => '<p>Проверенный текст Б</p>', 'status' => 'published',
            'museum_section_id' => $right->id,
        ]);
        $stale = MuseumApprovalRevision::fingerprint($a->fresh());

        // Both editors continuously take turns within one actual DB. Ensure a
        // mistaken cross-section update is denied and changes do not leak.
        for ($i = 1; $i <= 15; ++$i) {
            $this->actingAs($editorA, 'moonshine');
            $a->refresh()->update(['body' => '<p>Редакция А '.$i.'</p>']);
            $this->actingAs($editorB, 'moonshine');
            $b->refresh()->update(['body' => '<p>Редакция Б '.$i.'</p>']);
            try {
                $a->refresh()->update(['body' => '<p>Неавторизованная подмена '.$i.'</p>']);
                $this->fail('Editor B modified a different section');
            } catch (AuthorizationException) {
                $this->assertSame('<p>Редакция А '.$i.'</p>', $a->fresh()->body);
            }
        }

        $this->actingAs($admin, 'moonshine');
        $url = route('museum.entries.approve-and-queue', $a);
        $this->post($url, ['revision_sha256' => $stale])->assertStatus(409);
        $this->assertDatabaseCount('museum_content_approvals', 0);
        $this->assertDatabaseCount('museum_publication_runs', 0);
        $current = MuseumApprovalRevision::fingerprint($a->fresh());
        $this->assertNotSame($stale, $current);

        $this->post($url, ['revision_sha256' => $current])->assertRedirect();
        for ($i = 0; $i < 10; ++$i) {
            $this->post($url, ['revision_sha256' => $current])->assertRedirect();
        }
        $this->assertDatabaseCount('museum_content_approvals', 1);
        $this->assertDatabaseCount('museum_publication_runs', 1);
        $this->assertSame($current, MuseumContentApproval::sole()->revision_sha256);
        $this->assertSame('queued', MuseumPublicationRun::sole()->status);
        Queue::assertPushed(PublishMuseumSnapshot::class, 1);
        $this->assertSame('<p>Редакция Б 15</p>', $b->fresh()->body);
    }
}
