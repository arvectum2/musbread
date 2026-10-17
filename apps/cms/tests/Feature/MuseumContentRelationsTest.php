<?php

namespace Tests\Feature;

use App\Models\MuseumEntry;
use App\Models\MuseumEvent;
use App\Models\MuseumSection;
use Illuminate\Foundation\Testing\RefreshDatabase;
use MoonShine\Laravel\Models\MoonshineUser;
use MoonShine\Laravel\Models\MoonshineUserRole;
use Tests\TestCase;

class MuseumContentRelationsTest extends TestCase
{
    use RefreshDatabase;

    private function entry(string $slug, ?int $section = null, string $type = 'page'): MuseumEntry
    {
        return MuseumEntry::create([
            'slug' => $slug, 'title' => $slug, 'body' => 'Контент '.$slug,
            'type' => $type, 'status' => 'draft', 'museum_section_id' => $section,
        ]);
    }

    private function event(string $slug): MuseumEvent
    {
        return MuseumEvent::create([
            'slug' => $slug, 'title' => $slug, 'category' => 'Выставка',
            'starts_at' => '2026-11-21', 'body' => 'Программа', 'excerpt' => 'Анонс',
            'status' => 'draft',
        ]);
    }

    public function test_guest_cannot_read_or_write_relationships(): void
    {
        $source = $this->entry('private-relationship');
        $this->get(route('museum.entries.relations.edit', $source->id))
            ->assertRedirect('/admin/login')->assertDontSee('Контент private-relationship');
        $this->put(route('museum.entries.relations.update', $source->id), [
            'related_entry_ids' => [17],
        ])->assertRedirect('/admin/login');
    }

    public function test_admin_can_attach_view_clear_and_remove_related_entries_and_events(): void
    {
        $source = $this->entry('source');
        $target = $this->entry('excursion-target', null, 'excursion');
        $document = $this->entry('document-target', null, 'document');
        $event = $this->event('event-target');
        $this->actingAs(MoonshineUser::factory()->create(), 'moonshine');
        $form = route('museum.entries.relations.edit', $source->id);
        $this->get($form)->assertOk()->assertSee('excursion-target')
            ->assertSee('document-target')->assertSee('event-target')
            ->assertHeader('X-Robots-Tag', 'noindex, nofollow, noarchive');
        $this->put(route('museum.entries.relations.update', $source->id), [
            'related_entry_ids' => [$target->id, $document->id],
            'related_event_ids' => [$event->id],
        ])->assertRedirect($form);
        $this->assertEqualsCanonicalizing([$target->id, $document->id],
            $source->relatedEntries()->pluck('museum_entries.id')->all());
        $this->assertSame([$event->id], $source->linkedEvents()->pluck('museum_events.id')->all());
        $this->assertSame([$source->id], $event->relatedEntries()->pluck('museum_entries.id')->all());
        $this->get($form)->assertOk()->assertSee('Связанные материалы');
        $this->put(route('museum.entries.relations.update', $source->id), [])->assertRedirect($form);
        $this->assertSame(0, $source->relatedEntries()->count());
        $this->assertSame(0, $source->linkedEvents()->count());
    }

    public function test_editor_only_sees_and_links_own_sections_and_cannot_guess_foreign_ids(): void
    {
        $own = MuseumSection::create(['slug' => 'own-section', 'title' => 'Свой', 'status' => 'published']);
        $foreign = MuseumSection::create(['slug' => 'foreign-section', 'title' => 'Чужой', 'status' => 'published']);
        $source = $this->entry('editor-source', $own->id);
        $allowed = $this->entry('allowed', $own->id);
        $denied = $this->entry('super-private', $foreign->id);
        $event = $this->event('visible-event');
        $event->update(['museum_section_id' => $own->id]);
        $foreignEvent = $this->event('classified-event');
        $foreignEvent->update(['museum_section_id' => $foreign->id]);
        $role = MoonshineUserRole::query()->firstOrCreate(['name' => 'Editor']);
        $editor = MoonshineUser::factory()->create(['moonshine_user_role_id' => $role->id]);
        $own->editors()->attach($editor->id);
        $this->actingAs($editor, 'moonshine');
        $this->get(route('museum.entries.relations.edit', $source->id))
            ->assertOk()->assertSee('allowed')->assertSee('visible-event')
            ->assertDontSee('super-private')->assertDontSee('classified-event');
        $this->get(route('museum.entries.relations.edit', $denied->id))->assertNotFound();
        $this->put(route('museum.entries.relations.update', $denied->id), [
            'related_entry_ids' => [$allowed->id],
        ])->assertNotFound();
        $this->put(route('museum.entries.relations.update', $source->id), [
            'related_entry_ids' => [$denied->id], 'related_event_ids' => [$event->id],
        ])->assertSessionHasErrors('related_entry_ids');
        $this->assertSame(0, $source->linkedEvents()->count());
        $this->put(route('museum.entries.relations.update', $source->id), [
            'related_entry_ids' => [$allowed->id], 'related_event_ids' => [$event->id],
        ])->assertRedirect();
        $this->assertSame(1, $source->relatedEntries()->count());
        $this->assertSame(1, $source->linkedEvents()->count());
        $this->put(route('museum.entries.relations.update', $source->id), [
            'related_entry_ids' => [$allowed->id], 'related_event_ids' => [$foreignEvent->id],
        ])->assertSessionHasErrors('related_event_ids');
        $this->assertSame([$event->id], $source->linkedEvents()->pluck('museum_events.id')->all());
    }

    public function test_self_link_duplicate_bad_types_and_unknown_targets_are_rejected(): void
    {
        $source = $this->entry('self-source');
        $target = $this->entry('valid-target');
        $this->actingAs(MoonshineUser::factory()->create(), 'moonshine');
        $url = route('museum.entries.relations.update', $source->id);
        $this->put($url, ['related_entry_ids' => [$source->id]])->assertSessionHasErrors('related_entry_ids');
        $this->put($url, ['related_entry_ids' => [$target->id, $target->id]])->assertSessionHasErrors('related_entry_ids.1');
        $this->put($url, ['related_event_ids' => [999999]])->assertSessionHasErrors('related_event_ids.0');
        $this->put($url, ['related_entry_ids' => 'bad'])->assertSessionHasErrors('related_entry_ids');
        $this->assertSame(0, $source->relatedEntries()->count());
        $this->get('/admin/museum-entries/not-numeric/relations')->assertNotFound();
    }

    public function test_deleting_target_and_source_removes_pivot_rows_with_foreign_keys(): void
    {
        $source = $this->entry('source-delete');
        $target = $this->entry('target-delete');
        $event = $this->event('event-delete');
        $source->relatedEntries()->attach($target->id);
        $source->linkedEvents()->attach($event->id);
        $target->delete();
        $this->assertSame(0, $source->relatedEntries()->count());
        $event->delete();
        $this->assertSame(0, $source->linkedEvents()->count());
    }
}
