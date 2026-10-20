<?php

namespace Tests\Feature;

use App\Models\MuseumDocument;
use App\Models\MuseumEntry;
use App\Models\MuseumMedia;
use App\Models\MuseumSection;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Http\UploadedFile;
use Illuminate\Support\Facades\Storage;
use MoonShine\Laravel\Models\MoonshineUser;
use MoonShine\Laravel\Models\MoonshineUserRole;
use Tests\TestCase;

/** End-to-end private Laravel routing from edit -> media/documents -> check. */
final class MuseumEditorialWorkflowNavigationTest extends TestCase
{
    use RefreshDatabase;

    private function entry(string $slug, int $sectionId): MuseumEntry
    {
        return MuseumEntry::create([
            'type' => 'news',
            'title' => 'Материал '.$slug,
            'slug' => $slug,
            'body' => '<p>Тестовая редакция.</p>',
            'status' => 'draft',
            'museum_section_id' => $sectionId,
        ]);
    }

    private function pdf(): UploadedFile
    {
        return UploadedFile::fake()->createWithContent(
            'manual.pdf', "%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n<<>>\n%%EOF\n"
        );
    }

    public function test_one_material_has_safe_linked_editorial_journey_and_keeps_context_on_upload(): void
    {
        Storage::fake('local');
        $section = MuseumSection::create([
            'slug' => 'editorial-journey-area', 'title' => 'Раздел редактора', 'status' => 'published',
        ]);
        $one = $this->entry('journey-first', $section->id);
        $two = $this->entry('journey-second', $section->id);
        $this->actingAs(MoonshineUser::factory()->create(), 'moonshine');

        $editorUrl = '/admin/resource/museum-entry-resource/museum-entry-form-page/'.$one->id;
        $this->get($editorUrl)->assertOk()
            ->assertSee('Маршрут редактора')
            ->assertSee(route('museum.media.index', ['entry' => $one->id]), false)
            ->assertSee(route('museum.documents.index', ['entry' => $one->id]), false)
            ->assertSee(route('museum.entries.preview', $one), false)
            ->assertSee('последнюю сохранённую редакцию');

        $mediaUrl = route('museum.media.index', ['entry' => $one->id]);
        $docsUrl = route('museum.documents.index', ['entry' => $one->id]);
        $this->get($mediaUrl)->assertOk()
            ->assertSee('Текущий материал: '.$one->title)
            ->assertSee('Вся медиатека')
            ->assertSee('value="'.$one->id.'" selected', false)
            ->assertSee($editorUrl, false);
        $this->get($docsUrl)->assertOk()
            ->assertSee('Текущий материал: '.$one->title)
            ->assertSee('Все документы')
            ->assertSee('value="'.$one->id.'" selected', false)
            ->assertSee($editorUrl, false);

        // An invalid upload must return to the scoped form, keep its
        // selected entry, and leave all original/private files untouched.
        $this->from($mediaUrl)->post(route('museum.media.store', ['entry' => $one->id]), [
            'museum_entry_id' => $one->id,
            'alt' => '',
            'image' => UploadedFile::fake()->image('invalid-alt.png', 40, 40),
        ])->assertRedirect($mediaUrl)->assertSessionHasErrors('alt');
        $this->from($docsUrl)->post(route('museum.documents.store', ['entry' => $one->id]), [
            'museum_entry_id' => $one->id,
            'label' => '',
            'document' => $this->pdf(),
        ])->assertRedirect($docsUrl)->assertSessionHasErrors('label');
        $this->assertDatabaseCount('museum_media', 0);
        $this->assertDatabaseCount('museum_documents', 0);
        $this->get($mediaUrl)->assertOk()
            ->assertSee('value="'.$one->id.'" selected', false);
        $this->get($docsUrl)->assertOk()
            ->assertSee('value="'.$one->id.'" selected', false);

        $this->post(route('museum.media.store', ['entry' => $one->id]), [
            'museum_entry_id' => $one->id,
            'alt' => 'Кирпичная печь в музее рядом с тестовой лопатой',
            'image' => UploadedFile::fake()->image('test.png', 80, 60),
        ])->assertRedirect($mediaUrl);
        $this->post(route('museum.documents.store', ['entry' => $one->id]), [
            'museum_entry_id' => $one->id,
            'label' => 'Доступное название тестового документа',
            'document' => $this->pdf(),
        ])->assertRedirect($docsUrl);
        $this->assertDatabaseHas('museum_media', ['museum_entry_id' => $one->id]);
        $this->assertDatabaseHas('museum_documents', ['museum_entry_id' => $one->id]);
        $this->get($mediaUrl)->assertOk()->assertSee('Кирпичная печь в музее');
        $this->get($docsUrl)->assertOk()->assertSee('Доступное название тестового документа');

        // Scoped display must not mix another editor's material.
        $this->post(route('museum.media.store', ['entry' => $two->id]), [
            'museum_entry_id' => $two->id,
            'alt' => 'Письменный музейный ярлык рядом с витриной',
            'image' => UploadedFile::fake()->image('other.png', 50, 45),
        ])->assertRedirect(route('museum.media.index', ['entry' => $two->id]));
        $this->post(route('museum.documents.store', ['entry' => $two->id]), [
            'museum_entry_id' => $two->id,
            'label' => 'Другой документ в редакторском разделе',
            'document' => $this->pdf(),
        ])->assertRedirect(route('museum.documents.index', ['entry' => $two->id]));
        $this->get($mediaUrl)->assertDontSee('Письменный музейный ярлык');
        $this->get($docsUrl)->assertDontSee('Другой документ в редакторском разделе');

        $media = MuseumMedia::where('museum_entry_id', $one->id)->firstOrFail();
        $doc = MuseumDocument::where('museum_entry_id', $one->id)->firstOrFail();
        $this->patch(route('museum.media.update', ['media' => $media->id, 'entry' => $one->id]), [
            'museum_entry_id' => $one->id,
            'alt' => 'Исправленная подпись печи и музейного экспоната',
        ])->assertRedirect($mediaUrl);
        $this->patch(route('museum.documents.accessibility', [
            'document' => $doc->id, 'entry' => $one->id,
        ]), [
            'accessibility_note' => 'Документ доступен для скачивания и просмотра; здесь описан его формат и назначение.',
            'accessibility_reviewed' => '1',
        ])->assertRedirect($docsUrl);
        $this->assertTrue($doc->fresh()->accessibility_reviewed);
        $this->get(route('museum.entries.preview', ['entry' => $one->id]))
            ->assertOk()->assertSee('Материал journey-first');
        $this->get(route('museum.content.preflight'))->assertOk()
            ->assertSee(route('museum.media.index', ['entry' => $one->id]), false)
            ->assertSee(route('museum.documents.index', ['entry' => $one->id]), false);
    }

    public function test_context_is_scoped_by_editor_access_and_malformed_queries_fail_closed(): void
    {
        $allowed = MuseumSection::create([
            'slug' => 'only-my-section', 'title' => 'Мой раздел', 'status' => 'published',
        ]);
        $private = MuseumSection::create([
            'slug' => 'not-my-section', 'title' => 'Чужой раздел', 'status' => 'published',
        ]);
        $mine = $this->entry('mine', $allowed->id);
        $secret = $this->entry('secret', $private->id);
        $role = MoonshineUserRole::where('name', 'Editor')->firstOrFail();
        $editor = MoonshineUser::factory()->create(['moonshine_user_role_id' => $role->id]);
        $allowed->editors()->attach($editor->id);

        $this->get(route('museum.media.index', ['entry' => $mine->id]))
            ->assertRedirect('/admin/login');
        $this->actingAs($editor, 'moonshine');
        foreach (['museum.media.index','museum.documents.index'] as $route) {
            $this->get(route($route, ['entry' => $mine->id]))->assertOk()
                ->assertSee('Текущий материал: '.$mine->title);
            $this->get(route($route, ['entry' => $secret->id]))->assertNotFound()
                ->assertDontSee($secret->title);
            $this->get(route($route).'?entry=invalid')->assertNotFound();
            $this->get(route($route).'?entry[]=1')->assertNotFound();
        }
        $this->get('/admin/resource/museum-entry-resource/museum-entry-form-page/'.$secret->id)
            ->assertNotFound();
    }

    public function test_new_entry_form_does_not_link_to_uncreated_media_or_preview(): void
    {
        $this->actingAs(MoonshineUser::factory()->create(), 'moonshine');
        $this->get('/admin/resource/museum-entry-resource/museum-entry-form-page')
            ->assertOk()->assertSee('сохраните новый материал')
            ->assertDontSee('href="'.route('museum.media.index', ['entry' => 0]).'"', false);
    }
}
