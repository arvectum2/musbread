<?php

namespace Tests\Feature;

use App\Models\MuseumSection;
use App\Models\MuseumEntry;
use App\Support\MuseumSectionAccess;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Validation\ValidationException;
use MoonShine\Laravel\Models\MoonshineUser;
use MoonShine\Laravel\Models\MoonshineUserRole;
use Tests\TestCase;

class MuseumSectionTest extends TestCase
{
    use RefreshDatabase;

    private function section(string $slug, ?int $parent = null, string $status = 'published'): MuseumSection
    {
        return MuseumSection::create([
            'slug' => $slug, 'title' => 'Раздел '.$slug,
            'parent_id' => $parent, 'status' => $status,
        ]);
    }

    private function editor(): MoonshineUser
    {
        $role = MoonshineUserRole::query()->where('name', 'Editor')->firstOrFail();
        return MoonshineUser::factory()->create(['moonshine_user_role_id' => $role->id]);
    }

    public function test_admin_can_create_reorder_and_move_sections_through_moonshine(): void
    {
        $this->actingAs(MoonshineUser::factory()->create(), 'moonshine');
        $this->post('/admin/resource/museum-section-resource/crud', [
            'slug' => 'museum', 'title' => 'Музей', 'status' => 'published', 'sort_order' => 3,
        ])->assertRedirect();
        $museum = MuseumSection::where('slug', 'museum')->firstOrFail();
        $this->post('/admin/resource/museum-section-resource/crud', [
            'slug' => 'history', 'title' => 'История', 'parent_id' => $museum->id,
            'status' => 'published', 'sort_order' => 12,
        ])->assertRedirect();
        $history = MuseumSection::where('slug', 'history')->firstOrFail();
        $this->assertSame($museum->id, $history->parent_id);
        $this->patch('/admin/resource/museum-section-resource/crud/'.$history->id, [
            'slug' => 'history', 'title' => 'История музея',
            'parent_id' => $museum->id, 'status' => 'published', 'sort_order' => 1,
        ])->assertRedirect();
        $this->assertSame(1, $history->fresh()->sort_order);
    }

    public function test_admin_can_open_edit_section_and_grant_editor_ui(): void
    {
        $admin = MoonshineUser::factory()->create();
        $section = $this->section('section-with-grants');
        $editor = $this->editor();
        $this->actingAs($admin, 'moonshine')
            ->get('/admin/resource/museum-section-resource/museum-section-form-page/'.$section->id)
            ->assertOk()
            ->assertSee('Назначенные редакторы');
        $section->editors()->attach($editor->id);
        $this->assertTrue(MuseumSectionAccess::mayEdit($editor, $section->id));
    }

    public function test_admin_grants_editor_section_rights_through_form(): void
    {
        $section = $this->section('museum-branch');
        $editor = $this->editor();
        $admin = MoonshineUser::factory()->create();

        $this->actingAs($admin, 'moonshine')
            ->patch('/admin/resource/museum-section-resource/crud/'.$section->id, [
                'slug' => $section->slug,
                'title' => 'Музейный раздел',
                'parent_id' => null,
                'status' => 'published',
                'sort_order' => 0,
                'editors' => [$editor->id],
            ])->assertRedirect();

        $this->assertDatabaseHas('museum_section_editor', [
            'museum_section_id' => $section->id,
            'moonshine_user_id' => $editor->id,
        ]);
    }

    public function test_editor_cannot_open_or_create_section_directly(): void
    {
        $this->actingAs($this->editor(), 'moonshine');
        $this->get('/admin/resource/museum-section-resource/museum-section-index-page')->assertForbidden();
        $this->post('/admin/resource/museum-section-resource/crud', [
            'slug' => 'forged-section', 'title' => 'Поддельный',
            'status' => 'published', 'sort_order' => 0,
        ])->assertForbidden();
        $this->assertDatabaseMissing('museum_sections', ['slug' => 'forged-section']);
    }

    public function test_cannot_create_parent_cycle_or_self_parent(): void
    {
        $parent = $this->section('parent');
        $child = $this->section('child', $parent->id);
        try {
            $parent->parent_id = $child->id;
            $parent->save();
            $this->fail('Cycle must be rejected');
        } catch (ValidationException $e) {
            $this->assertArrayHasKey('parent_id', $e->errors());
        }
        $this->assertNull($parent->fresh()->parent_id);
        $this->expectException(ValidationException::class);
        $child->parent_id = $child->id;
        $child->save();
    }

    public function test_deleting_nonempty_section_is_rejected(): void
    {
        $parent = $this->section('parent');
        $this->section('child', $parent->id);
        $this->expectException(ValidationException::class);
        $parent->delete();
    }

    public function test_deleting_section_with_material_is_rejected(): void
    {
        $section = $this->section('museum');
        MuseumEntry::create([
            'slug' => 'story', 'type' => 'page', 'title' => 'Материал',
            'body' => 'Контент', 'status' => 'draft',
            'museum_section_id' => $section->id,
        ]);
        $this->expectException(ValidationException::class);
        $section->delete();
    }

    public function test_empty_leaf_section_can_be_removed(): void
    {
        $section = $this->section('temporary');
        $section->delete();
        $this->assertDatabaseMissing('museum_sections', ['slug' => 'temporary']);
    }

    public function test_section_grants_default_deny_and_do_not_inherit(): void
    {
        $root = $this->section('root');
        $child = $this->section('child', $root->id);
        $editor = $this->editor();
        $this->assertFalse(MuseumSectionAccess::mayEdit($editor, $root->id));
        $root->editors()->attach($editor->id);
        $this->assertTrue(MuseumSectionAccess::mayEdit($editor, $root->id));
        $this->assertFalse(MuseumSectionAccess::mayEdit($editor, $child->id));
        $this->assertSame([$root->id], MuseumSectionAccess::allowedIds($editor));
    }

    public function test_editor_only_sees_and_edits_assigned_materials(): void
    {
        $assigned = $this->section('assigned');
        $private = $this->section('private');
        $editor = $this->editor();
        $assigned->editors()->attach($editor->id);
        $this->actingAs($editor, 'moonshine');
        $this->post('/admin/resource/museum-entry-resource/crud', [
            'slug' => 'allowed', 'type' => 'page', 'title' => 'Разрешено',
            'body' => 'Текст', 'status' => 'draft', 'museum_section_id' => $assigned->id,
        ])->assertRedirect();
        $this->post('/admin/resource/museum-entry-resource/crud', [
            'slug' => 'forbidden', 'type' => 'page', 'title' => 'Запрещено',
            'body' => 'Текст', 'status' => 'draft', 'museum_section_id' => $private->id,
        ])->assertForbidden();
        $this->assertDatabaseHas('museum_entries', ['slug' => 'allowed']);
        $this->assertDatabaseMissing('museum_entries', ['slug' => 'forbidden']);
        auth('moonshine')->logout();
        $other = MuseumEntry::create([
            'slug' => 'other', 'type' => 'page', 'title' => 'Чужой',
            'body' => 'Текст', 'status' => 'draft',
            'museum_section_id' => $private->id,
        ]);
        $this->actingAs($editor, 'moonshine');
        $this->assertEqualsCanonicalizing(['allowed'],
            MuseumEntry::query()->editableBy($editor)->pluck('slug')->all());
        $this->get('/admin/resource/museum-entry-resource/museum-entry-form-page/'.$other->id)
            ->assertStatus(404);
    }

    public function test_editor_cannot_reassign_own_material_to_private_section(): void
    {
        $assigned = $this->section('assigned');
        $private = $this->section('private');
        $editor = $this->editor();
        $assigned->editors()->attach($editor->id);
        $entry = MuseumEntry::create([
            'slug' => 'before', 'title' => 'Редактор', 'type' => 'page',
            'body' => 'Текст', 'status' => 'draft',
            'museum_section_id' => $assigned->id,
        ]);
        $this->actingAs($editor, 'moonshine');
        $this->patch('/admin/resource/museum-entry-resource/crud/'.$entry->id, [
            'slug' => 'before', 'title' => 'Попытка',
            'type' => 'page', 'body' => 'Текст',
            'status' => 'draft', 'museum_section_id' => $private->id,
        ])->assertForbidden();
        $this->assertSame($assigned->id, $entry->fresh()->museum_section_id);
    }
}
