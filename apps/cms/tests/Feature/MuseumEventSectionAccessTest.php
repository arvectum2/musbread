<?php

namespace Tests\Feature;

use App\Models\MuseumEvent;
use App\Models\MuseumSection;
use App\Support\MuseumContentPreflight;
use Illuminate\Auth\Access\AuthorizationException;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Validation\ValidationException;
use MoonShine\Laravel\Models\MoonshineUser;
use MoonShine\Laravel\Models\MoonshineUserRole;
use Tests\TestCase;

class MuseumEventSectionAccessTest extends TestCase
{
    use RefreshDatabase;

    private function section(string $slug, ?int $parent = null, string $status = 'published'): MuseumSection
    {
        return MuseumSection::create([
            'slug'=>$slug,'title'=>'Раздел '.$slug,'parent_id'=>$parent,'status'=>$status,
        ]);
    }

    private function editor(MuseumSection $section): MoonshineUser
    {
        $role = MoonshineUserRole::query()->where('name', 'Editor')->firstOrFail();
        $editor = MoonshineUser::factory()->create(['moonshine_user_role_id'=>$role->id]);
        $section->editors()->attach($editor->id);
        return $editor;
    }

    private function event(string $slug, ?MuseumSection $section = null, string $status = 'draft'): MuseumEvent
    {
        return MuseumEvent::create([
            'slug'=>$slug, 'title'=>'Событие '.$slug,
            'category'=>'Выставка', 'starts_at'=>now()->addDay()->toDateString(),
            'excerpt'=>'Редакционный анонс', 'body'=>'Редакционный текст',
            'status'=>$status, 'museum_section_id'=>$section?->id,
        ]);
    }

    private function export(): array
    {
        $target = storage_path('framework/testing/scoped-event-test.json');
        $manifest = storage_path('framework/testing/scoped-event-manifest.json');
        try {
            $this->artisan('museum:export', [
                '--output'=>$target, '--manifest'=>$manifest,
            ])->assertSuccessful();
            return json_decode(file_get_contents($target), true, flags: JSON_THROW_ON_ERROR);
        } finally {
            @unlink($target);
            @unlink($manifest);
        }
    }

    public function test_editor_crud_and_preview_are_limited_to_explicit_grant(): void
    {
        $mine = $this->section('owned');
        $other = $this->section('other');
        $editor = $this->editor($mine);
        $assigned = $this->event('owned-event', $mine);
        $hidden = $this->event('hidden-event', $other);
        $legacy = $this->event('legacy-unassigned');
        $this->actingAs($editor, 'moonshine');
        $index = $this->get('/admin/resource/museum-event-resource/museum-event-index-page')
            ->assertOk()->assertSee('owned-event')->assertDontSee('hidden-event')
            ->assertDontSee('legacy-unassigned');
        $this->get(route('museum.events.preview', $assigned->id))->assertOk();
        $this->get(route('museum.events.preview', $hidden->id))->assertNotFound();
        $this->get(route('museum.events.preview', $legacy->id))->assertNotFound();
        $this->get('/admin/resource/museum-event-resource/museum-event-form-page/'.$hidden->id)
            ->assertNotFound();

        $payload = [
            'slug'=>'edit-new', 'title'=>'Создано редактором', 'category'=>'Выставка',
            'starts_at'=>now()->addWeek()->toDateString(), 'excerpt'=>'Событие',
            'body'=>'Описание', 'status'=>'draft',
        ];
        $this->post('/admin/resource/museum-event-resource/crud', $payload + [
            'museum_section_id'=>$other->id,
        ])->assertForbidden();
        $this->assertDatabaseMissing('museum_events', ['slug'=>'edit-new']);
        $this->post('/admin/resource/museum-event-resource/crud', $payload + [
            'museum_section_id'=>$mine->id,
        ])->assertRedirect();
        $this->assertDatabaseHas('museum_events', ['slug'=>'edit-new', 'museum_section_id'=>$mine->id]);
        // The CMS form may redirect with a validation error before hitting
        // the model authorization hook. In both paths persistence MUST fail.
        $this->patch('/admin/resource/museum-event-resource/crud/'.$assigned->id, $payload + [
            'museum_section_id'=>$other->id,
        ])->assertRedirect();
        $this->assertSame($mine->id, $assigned->fresh()->museum_section_id);
        $this->assertSame(2, MuseumEvent::query()->editableBy($editor)->count());
    }

    public function test_revocation_and_deletion_do_not_bypass_section_grants(): void
    {
        $section = $this->section('revocable');
        $editor = $this->editor($section);
        $event = $this->event('revocable-event', $section);
        $this->actingAs($editor, 'moonshine');
        $this->get(route('museum.events.preview', $event->id))->assertOk();
        $section->editors()->detach($editor->id);
        $this->get(route('museum.events.preview', $event->id))->assertNotFound();
        try {
            $event->delete();
            $this->fail('Revoked role must not delete');
        } catch (AuthorizationException $exception) {
            $this->assertDatabaseHas('museum_events', ['id'=>$event->id]);
        }
    }

    public function test_section_cannot_be_deleted_while_events_refer_to_it(): void
    {
        $section = $this->section('has-event');
        $this->event('event-before-deletion', $section);
        $this->expectException(ValidationException::class);
        $section->delete();
    }

    public function test_draft_parent_blocks_event_export_and_preflight(): void
    {
        $root = $this->section('closed-parent', null, 'draft');
        $child = $this->section('child-events', $root->id);
        $open = $this->section('open-events');
        $blocked = $this->event('blocked-event', $child, 'published');
        $ready = $this->event('allowed-event', $open, 'published');
        $old = $this->event('legacy-event', null, 'published');

        $json = $this->export();
        $this->assertEqualsCanonicalizing(['allowed-event','legacy-event'], array_column($json['events'], 'slug'));
        $this->assertSame($open->slug, collect($json['events'])->firstWhere('slug', 'allowed-event')['section_slug']);
        $this->assertArrayNotHasKey('section_slug', collect($json['events'])->firstWhere('slug','legacy-event'));
        $this->assertNotContains('blocked-event', array_column($json['events'], 'slug'));

        $report = app(MuseumContentPreflight::class)->report();
        $this->assertSame('blocked', collect($report['events'])->firstWhere('id', $blocked->id)['state']);
        $this->assertSame('ready', collect($report['events'])->firstWhere('id', $ready->id)['state']);

        $editor = $this->editor($open);
        $filtered = app(MuseumContentPreflight::class)->report($editor);
        $this->assertSame(1, $filtered['events_total']);
        $this->assertSame('allowed-event', $filtered['events'][0]['slug']);
        $this->assertNotContains('legacy-event', array_column($filtered['events'], 'slug'));
    }

    public function test_administrator_retains_legacy_event_access(): void
    {
        $legacy = $this->event('legacy-admin-only');
        $this->actingAs(MoonshineUser::factory()->create(), 'moonshine');
        $this->get(route('museum.events.preview', $legacy->id))->assertOk();
        $this->get('/admin/resource/museum-event-resource/museum-event-index-page')
            ->assertOk()->assertSee('legacy-admin-only');
    }
}
