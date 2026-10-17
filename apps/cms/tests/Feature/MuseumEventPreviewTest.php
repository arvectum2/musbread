<?php

namespace Tests\Feature;

use App\Models\MuseumEvent;
use App\Models\MuseumSection;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\DB;
use MoonShine\Laravel\Models\MoonshineUser;
use MoonShine\Laravel\Models\MoonshineUserRole;
use Tests\TestCase;

class MuseumEventPreviewTest extends TestCase
{
    use RefreshDatabase;

    private function event(): MuseumEvent
    {
        return MuseumEvent::create([
            'slug' => 'draft-event-preview', 'title' => 'Пример закрытого события',
            'category' => 'Выставка', 'starts_at' => now()->addDays(5)->toDateString(),
            'excerpt' => 'Анонс для редактора', 'body' => '<p>Содержимое события</p>',
            'status' => 'draft',
        ]);
    }

    public function test_anonymous_event_preview_is_closed_and_id_guessing_returns_404(): void
    {
        $event = $this->event();
        $this->get(route('museum.events.preview', $event->id))->assertRedirect('/admin/login');
        $this->actingAs(MoonshineUser::factory()->create(), 'moonshine')
            ->get('/admin/museum-events/not-numeric/preview')->assertNotFound();
        $this->get('/admin/museum-events/999999/preview')->assertNotFound();
    }

    public function test_authorized_editor_previews_saved_event_with_noindex_and_no_publication(): void
    {
        $event = $this->event();
        $role = MoonshineUserRole::query()->firstOrCreate(['name' => 'Editor']);
        $editor = MoonshineUser::factory()->create(['moonshine_user_role_id' => $role->id]);
        $section = MuseumSection::create(['slug'=>'event-owner','title'=>'Мероприятия','status'=>'published']);
        $section->editors()->attach($editor->id);
        $event->update(['museum_section_id'=>$section->id]);
        $this->actingAs($editor, 'moonshine');
        $url = route('museum.events.preview', $event->id);
        $this->get($url)->assertOk()->assertSee('Пример закрытого события')
            ->assertSee('Содержимое события')->assertSee('Черновик')
            ->assertHeader('Cache-Control', 'max-age=0, no-store, private')
            ->assertHeader('X-Robots-Tag', 'noindex, nofollow, noarchive');
        $this->get('/admin/resource/museum-event-resource/museum-event-index-page')
            ->assertOk()->assertSee($url, false);
        $this->assertFalse(MuseumEvent::query()->public()->whereKey($event->id)->exists());
        $event->update(['status'=>'published', 'published_at'=>now()->addWeek()]);
        $this->get($url)->assertOk()->assertSee('Помечен к публикации');
        $this->assertFalse(MuseumEvent::query()->public()->whereKey($event->id)->exists());
    }

    public function test_unsafe_event_html_is_cleaned_on_preview_even_if_persisted_directly(): void
    {
        $event = $this->event();
        DB::table('museum_events')->where('id', $event->id)->update([
            'title' => '<img src=x onerror=evil()>',
            'body' => '<p>Безопасное тело</p><script>evil()</script><a href="javascript:evil()">Ссылка</a>',
        ]);
        $this->actingAs(MoonshineUser::factory()->create(), 'moonshine')
            ->get(route('museum.events.preview', $event->id))
            ->assertOk()->assertSee('&lt;img', false)
            ->assertSee('<p>Безопасное тело</p>', false)
            ->assertDontSee('<script', false)->assertDontSee('href="javascript:', false)
            ->assertHeader('X-Frame-Options', 'DENY')
            ->assertHeader('Content-Security-Policy', "default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; object-src 'none'; form-action 'none'; frame-ancestors 'none'");
    }
}
