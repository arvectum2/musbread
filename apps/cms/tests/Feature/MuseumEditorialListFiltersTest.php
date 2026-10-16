<?php

namespace Tests\Feature;

use App\Models\MuseumEntry;
use App\Models\MuseumEvent;
use App\Models\MuseumSection;
use App\Support\MuseumEntryPublicationState;
use Illuminate\Foundation\Testing\RefreshDatabase;
use MoonShine\Laravel\Models\MoonshineUser;
use MoonShine\Laravel\Models\MoonshineUserRole;
use Tests\TestCase;

class MuseumEditorialListFiltersTest extends TestCase
{
    use RefreshDatabase;

    private const PATH = '/admin/resource/museum-entry-resource/museum-entry-index-page';

    private function section(string $slug, string $status = 'published', ?int $parent = null): MuseumSection
    {
        return MuseumSection::create([
            'title' => 'Рубрика '.$slug, 'slug' => $slug, 'status' => $status, 'parent_id' => $parent,
        ]);
    }

    private function item(string $slug, string $title, string $type = 'news',
        string $status = 'draft', ?string $date = null, ?int $sectionId = null): MuseumEntry
    {
        return MuseumEntry::create([
            'slug' => $slug, 'title' => $title, 'type' => $type,
            'body' => 'Нейтральный тестовый текст', 'status' => $status,
            'published_at' => $date, 'museum_section_id' => $sectionId,
        ]);
    }

    private function getFiltered(array $parameters): \Illuminate\Testing\TestResponse
    {
        return $this->get(self::PATH.'?'.http_build_query($parameters));
    }

    public function test_filters_are_present_and_title_slug_search_only_returns_matching_records(): void
    {
        $section = $this->section('search');
        $this->item('one-name', 'Уникальный заголовок', sectionId: $section->id);
        $this->item('another-address', 'Обычная публикация', sectionId: $section->id);
        $this->actingAs(MoonshineUser::factory()->create(), 'moonshine');
        $this->get(self::PATH)->assertOk()->assertSee('Тип материала')
            ->assertSee('Готовность к экспорту')->assertSee('Раздел сайта')
            ->assertSee('Публиковать с')->assertSee('Связанных материалов')
            ->assertSee('Событий');
        $this->getFiltered(['search' => 'Уникальный'])->assertOk()
            ->assertSee('Уникальный заголовок')->assertDontSee('Обычная публикация');
        $this->getFiltered(['search' => 'another-address'])->assertOk()
            ->assertSee('Обычная публикация')->assertDontSee('Уникальный заголовок');
        $this->getFiltered(['filter' => ['type' => 'news', 'status' => 'draft']])
            ->assertOk()->assertSee('Уникальный заголовок')->assertSee('Обычная публикация');
        $this->getFiltered(['filter' => ['type' => 'excursion']])
            ->assertOk()->assertDontSee('Уникальный заголовок');
    }

    public function test_export_readiness_filter_distinguishes_draft_scheduled_blocked_and_ready(): void
    {
        $live = $this->section('live');
        $hidden = $this->section('hidden', 'draft');
        $child = $this->section('child', 'published', $hidden->id);
        $this->item('draft-record', 'Редакционный черновик', sectionId: $live->id);
        $this->item('scheduled-record', 'Запланированный материал', status: 'published',
            date: now()->addDays(3)->toDateTimeString(), sectionId: $live->id);
        $this->item('blocked-record', 'Скрытая родительская ветка', status: 'published',
            date: now()->subDay()->toDateTimeString(), sectionId: $child->id);
        $this->item('ready-record', 'Готовая к выгрузке статья', status: 'published',
            date: now()->subDay()->toDateTimeString(), sectionId: $live->id);
        $this->actingAs(MoonshineUser::factory()->create(), 'moonshine');
        foreach ([
            'draft' => 'Редакционный черновик',
            'scheduled' => 'Запланированный материал',
            'blocked' => 'Скрытая родительская ветка',
            'ready' => 'Готовая к выгрузке статья',
        ] as $state => $expected) {
            $response = $this->getFiltered(['filter' => ['publication_state' => $state]])
                ->assertOk()->assertSee($expected);
            foreach (array_diff([
                'Редакционный черновик', 'Запланированный материал',
                'Скрытая родительская ветка', 'Готовая к выгрузке статья',
            ], [$expected]) as $absent) {
                $response->assertDontSee($absent);
            }
        }
        // Malformed filters must never become SQL identifiers or bypass ACL.
        $this->getFiltered(['filter' => ['publication_state' => 'unknown']])
            ->assertOk()->assertDontSee('Готовая к выгрузке статья');
    }

    public function test_editor_sees_only_granted_sections_search_results_and_related_counts(): void
    {
        $mine = $this->section('mine');
        $foreign = $this->section('foreign');
        $own = $this->item('my-editable', 'Свой секрет редактора', sectionId: $mine->id);
        $ownRelated = $this->item('own-related', 'Связь разрешена', sectionId: $mine->id);
        $private = $this->item('foreign-record', 'Чужая секретная новость', sectionId: $foreign->id);
        $own->relatedEntries()->attach([$ownRelated->id, $private->id]);
        $event = MuseumEvent::create([
            'slug' => 'editor-event', 'title' => 'Рубрика-афиша',
            'category' => 'Событие', 'starts_at' => '2026-11-20', 'excerpt' => 'Анонс',
            'body' => 'Программа', 'status' => 'draft',
        ]);
        $own->linkedEvents()->attach($event->id);
        $role = MoonshineUserRole::query()->where('name', 'Editor')->firstOrFail();
        $editor = MoonshineUser::factory()->create(['moonshine_user_role_id' => $role->id]);
        $mine->editors()->attach($editor->id);
        $this->actingAs($editor, 'moonshine');
        $this->get(self::PATH)->assertOk()
            ->assertSee('Свой секрет редактора')
            ->assertDontSee('Чужая секретная новость')
            ->assertDontSee('Рубрика foreign')
            ->assertSee('Рубрика mine');
        $this->getFiltered(['search' => 'Чужая секретная'])->assertOk()
            ->assertDontSee('Чужая секретная новость');
        $this->getFiltered(['filter' => ['museum_section_id' => $foreign->id]])
            ->assertOk()->assertDontSee('Чужая секретная новость')
            ->assertDontSee('Свой секрет редактора');
        $this->getFiltered(['filter' => ['museum_section_id' => $mine->id]])
            ->assertOk()->assertSee('Свой секрет редактора');
        // Two links in private pivot table; editor sees only one accessible target.
        $visible = $own->newQuery()->editableBy($editor)
            ->withCount(['relatedEntries as editorial_related_entries_count'
                => static fn ($q) => $q->editableBy($editor),
                'linkedEvents as editorial_linked_events_count'])
            ->findOrFail($own->id);
        $this->assertSame(1, $visible->editorial_related_entries_count);
        $this->assertSame(1, $visible->editorial_linked_events_count);
    }

    public function test_relationship_filter_respects_target_permissions_and_finds_unlinked_records(): void
    {
        $mine = $this->section('allowed-branch');
        $other = $this->section('hidden-branch');
        $linkedOnlyToForeign = $this->item('private-relation', 'Связан только с чужим', sectionId: $mine->id);
        $linkedToOwn = $this->item('public-relation', 'Связан со своим', sectionId: $mine->id);
        $target = $this->item('target', 'Цель связи', sectionId: $mine->id);
        $foreignTarget = $this->item('foreign-target', 'Чужая цель', sectionId: $other->id);
        $linkedOnlyToForeign->relatedEntries()->attach($foreignTarget->id);
        $linkedToOwn->relatedEntries()->attach($target->id);
        $editorRole = MoonshineUserRole::query()->where('name', 'Editor')->firstOrFail();
        $editor = MoonshineUser::factory()->create(['moonshine_user_role_id' => $editorRole->id]);
        $mine->editors()->attach($editor->id);
        $this->actingAs($editor, 'moonshine');
        $this->getFiltered(['filter' => ['link_state' => 'linked']])->assertOk()
            ->assertSee('Связан со своим')->assertDontSee('Связан только с чужим')
            ->assertDontSee('Чужая цель');
        $this->getFiltered(['filter' => ['link_state' => 'unlinked']])->assertOk()
            ->assertSee('Связан только с чужим')->assertDontSee('Связан со своим');
        $this->getFiltered(['filter' => ['link_state' => 'hack']])->assertOk()
            ->assertDontSee('Связан со своим')->assertDontSee('Связан только с чужим');
    }

    public function test_admin_can_find_legacy_unassigned_entries_without_leaking_to_editor(): void
    {
        $section = $this->section('assigned-section');
        $this->item('unassigned-legacy', 'Запись без назначенного раздела');
        $this->item('section-attached', 'Запись с разделом', sectionId: $section->id);
        $this->actingAs(MoonshineUser::factory()->create(), 'moonshine');
        $this->getFiltered(['filter' => ['museum_section_id' => 'unassigned']])
            ->assertOk()->assertSee('Запись без назначенного раздела')
            ->assertDontSee('Запись с разделом');
        $this->getFiltered(['filter' => ['museum_section_id' => 'nonsense']])
            ->assertOk()->assertDontSee('Запись без назначенного раздела');
        $this->getFiltered(['filter' => ['museum_section_id' => $section->id]])
            ->assertOk()->assertSee('Запись с разделом')
            ->assertDontSee('Запись без назначенного раздела');
    }

    public function test_publication_state_scope_handles_unassigned_records_and_invalid_states(): void
    {
        $entry = $this->item('legacy-unassigned', 'Легаси без раздела', status: 'published',
            date: now()->subDay()->toDateTimeString());
        $this->assertTrue(MuseumEntryPublicationState::apply(MuseumEntry::query(), 'ready')->whereKey($entry->id)->exists());
        $this->assertFalse(MuseumEntryPublicationState::apply(MuseumEntry::query(), 'blocked')->whereKey($entry->id)->exists());
        $this->assertFalse(MuseumEntryPublicationState::apply(MuseumEntry::query(), 'unknown')->whereKey($entry->id)->exists());
    }
}
