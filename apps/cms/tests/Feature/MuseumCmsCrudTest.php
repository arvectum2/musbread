<?php

namespace Tests\Feature;

use App\Models\MuseumEvent;
use Illuminate\Foundation\Testing\RefreshDatabase;
use MoonShine\Laravel\Models\MoonshineUser;
use Tests\TestCase;

class MuseumCmsCrudTest extends TestCase
{
    use RefreshDatabase;

    private function admin(): MoonshineUser
    {
        return MoonshineUser::factory()->create();
    }

    public function test_unauthenticated_user_cannot_open_event_editor(): void
    {
        $this->get('/admin/resource/museum-event-resource/museum-event-form-page')
            ->assertRedirect('/admin/login');
    }

    public function test_administrator_can_sign_in_through_moonshine_form(): void
    {
        $user = $this->admin();
        $this->post('/admin/authenticate', [
            'username' => $user->email, 'password' => 'password',
        ])->assertRedirect();
        $this->assertAuthenticatedAs($user, 'moonshine');
        $this->get('/admin')->assertOk();
    }

    public function test_administrator_can_open_event_editor(): void
    {
        $this->actingAs($this->admin(), 'moonshine')
            ->get('/admin/resource/museum-event-resource/museum-event-form-page')
            ->assertOk();
    }

    public function test_unauthenticated_user_cannot_post_event(): void
    {
        $this->post('/admin/resource/museum-event-resource/crud', [
            'slug' => 'blocked-event', 'title' => 'Test'
        ])->assertRedirect('/admin/login');
        $this->assertSame(0, MuseumEvent::count());
    }

    public function test_administrator_can_create_a_draft_through_resource_route(): void
    {
        $data = [
            'slug' => 'test-event-2026',
            'title' => 'Пробное событие',
            'category' => 'Выставка',
            'starts_at' => '2026-11-20',
            'excerpt' => 'Тестовый анонс',
            'body' => 'Тестовое описание',
            'status' => 'draft',
        ];
        $response = $this->actingAs($this->admin(), 'moonshine')
            ->post('/admin/resource/museum-event-resource/crud', $data);
        $this->assertDatabaseHas('museum_events', ['slug' => 'test-event-2026', 'status' => 'draft']);
        $response->assertStatus(302);
        $event = MuseumEvent::where('slug', 'test-event-2026')->firstOrFail();
        $this->assertNull($event->published_at);
    }

    public function test_logged_in_administrator_can_update_and_schedule_publication(): void
    {
        $event = MuseumEvent::create([
            'slug' => 'draft-event', 'title' => 'Черновик', 'category' => 'Выставка',
            'starts_at' => '2026-11-20', 'excerpt' => 'Анонс', 'body' => 'Текст',
            'status' => 'draft',
        ]);

        $this->actingAs($this->admin(), 'moonshine')
            ->get('/admin/resource/museum-event-resource/museum-event-form-page/'.$event->id)
            ->assertOk();

        $this->patch('/admin/resource/museum-event-resource/crud/'.$event->id, [
            'slug' => 'draft-event', 'title' => 'Обновлённое событие',
            'category' => 'Выставка', 'starts_at' => '2026-11-20',
            'excerpt' => 'Анонс', 'body' => 'Изменённое описание',
            'status' => 'published', 'published_at' => now()->addDays(4)->format('Y-m-d\TH:i'),
        ])->assertStatus(302);

        $event->refresh();
        $this->assertSame('Обновлённое событие', $event->title);
        $this->assertSame('published', $event->status);
        $this->assertFalse($event->newQuery()->public()->whereKey($event->id)->exists());
    }

    public function test_duplicate_slug_is_rejected_by_editor(): void
    {
        MuseumEvent::create([
            'slug' => 'taken-slug', 'title' => 'Первый',
            'category' => 'Экскурсия', 'starts_at' => '2026-11-20',
            'excerpt' => 'Анонс', 'body' => 'Описание', 'status' => 'draft',
        ]);
        $this->actingAs($this->admin(), 'moonshine')
            ->post('/admin/resource/museum-event-resource/crud', [
                'slug' => 'taken-slug', 'title' => 'Повтор',
                'category' => 'Экскурсия', 'starts_at' => '2026-11-20',
                'excerpt' => 'Анонс', 'body' => 'Описание', 'status' => 'draft',
            ])->assertStatus(302);
        $this->assertSame(1, MuseumEvent::count());
    }

    public function test_published_in_future_is_not_public_yet(): void
    {
        MuseumEvent::create([
            'slug' => 'future-event', 'title' => 'Событие', 'category' => 'Экскурсия',
            'starts_at' => now()->addDays(10)->toDateString(),
            'excerpt' => 'Анонс', 'body' => 'Описание', 'status' => 'published',
            'published_at' => now()->addDays(2),
        ]);
        $this->assertSame(0, MuseumEvent::public()->count());
        $this->assertSame(1, MuseumEvent::count());
    }
}
