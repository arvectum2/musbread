<?php

namespace Tests\Feature;

use App\Jobs\PublishMuseumSnapshot;
use App\Models\MuseumEntry;
use App\Models\MuseumPublicationRun;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Queue;
use MoonShine\Laravel\Models\MoonshineUser;
use MoonShine\Laravel\Models\MoonshineUserRole;
use Tests\TestCase;

class MuseumPublishRequestButtonTest extends TestCase
{
    use RefreshDatabase;

    protected function tearDown(): void
    {
        config(['museum.queue_publication' => false]);
        parent::tearDown();
    }

    public function test_guest_editor_and_disabled_queue_cannot_request_publication(): void
    {
        $this->post(route('museum.content.queue-publication'))->assertRedirect('/admin/login');

        $editorRole = MoonshineUserRole::where('name', 'Editor')->firstOrFail();
        $editor = MoonshineUser::factory()
            ->create(['moonshine_user_role_id' => $editorRole->id]);
        config(['museum.queue_publication' => true, 'queue.default' => 'database',
                 'cache.default' => 'database']);
        Queue::fake();
        $this->actingAs($editor, 'moonshine')
            ->post(route('museum.content.queue-publication'))->assertForbidden();
        $this->get(route('museum.content.preflight'))->assertOk()
            ->assertDontSee('Опубликовать — подготовить пакет в очереди');

        $admin = MoonshineUser::factory()->create();
        $this->actingAs($admin, 'moonshine');
        config(['museum.queue_publication' => false]);
        $this->post(route('museum.content.queue-publication'))->assertStatus(409);
        $this->get(route('museum.content.preflight'))->assertOk()
            ->assertSee('постоянная очередь не настроена')
            ->assertDontSee('Опубликовать — подготовить пакет в очереди');
        config(['museum.queue_publication' => true, 'queue.default' => 'sync']);
        $this->post(route('museum.content.queue-publication'))->assertStatus(409);
        config(['queue.default' => 'database', 'cache.default' => 'array']);
        $this->post(route('museum.content.queue-publication'))->assertStatus(409);
        Queue::assertNothingPushed();
        $this->assertDatabaseCount('museum_publication_runs', 0);
    }

    public function test_admin_click_queues_only_one_private_export_and_exposes_csrf_button(): void
    {
        $admin = MoonshineUser::factory()->create();
        $this->actingAs($admin, 'moonshine');
        config(['museum.queue_publication' => true, 'queue.default' => 'database',
                 'cache.default' => 'database']);
        Queue::fake();
        $this->get(route('museum.content.preflight'))->assertOk()
            ->assertSee('Опубликовать — подготовить пакет в очереди')
            ->assertSee('name="_token"', false)
            ->assertSee('method="post"', false);
        $this->post(route('museum.content.queue-publication'))->assertRedirect(route('museum.content.preflight'))
            ->assertSessionHas('museum_export_queue_result');
        $this->post(route('museum.content.queue-publication'))->assertRedirect(route('museum.content.preflight'));
        $this->assertDatabaseCount('museum_publication_runs', 1);
        $this->assertSame('queued', MuseumPublicationRun::first()->status);
        Queue::assertPushed(PublishMuseumSnapshot::class, 1);
        $this->get(route('museum.content.preflight'))->assertOk()
            ->assertSee('Это не подтверждение обновления публичного сайта');
    }

    public function test_critical_invalid_published_content_blocks_manual_button_and_export(): void
    {
        $admin = MoonshineUser::factory()->create();
        $this->actingAs($admin, 'moonshine');
        config(['museum.queue_publication' => true, 'queue.default' => 'database',
                 'cache.default' => 'database']);
        Queue::fake();
        MuseumEntry::create([
            'type' => 'news', 'slug' => 'bad-published-link',
            'title' => 'Неправильная ссылка',
            'body' => '<p><a href="/news/not-created/">missing news</a></p>',
            'status' => 'published',
        ]);
        $this->get(route('museum.content.preflight'))->assertOk()
            ->assertDontSee('Опубликовать — подготовить пакет в очереди')
            ->assertSee('есть критические ошибки в готовых материалах');
        $this->post(route('museum.content.queue-publication'))->assertStatus(422);
        Queue::assertNothingPushed();
        $this->assertDatabaseCount('museum_publication_runs', 0);
    }
}
