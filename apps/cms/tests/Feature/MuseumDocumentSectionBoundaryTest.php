<?php

namespace Tests\Feature;

use App\Models\MuseumDocument;
use App\Models\MuseumEntry;
use App\Models\MuseumSection;
use Illuminate\Foundation\Testing\RefreshDatabase;
use MoonShine\Laravel\Models\MoonshineUser;
use MoonShine\Laravel\Models\MoonshineUserRole;
use Tests\TestCase;

final class MuseumDocumentSectionBoundaryTest extends TestCase
{
    use RefreshDatabase;

    private function document(int $sectionId, string $slug): MuseumDocument
    {
        $entry = MuseumEntry::create([
            'type' => 'document', 'slug' => $slug,
            'title' => 'Документ раздела '.$slug,
            'body' => '<p>Тест доступа к материалу музея</p>',
            'status' => 'draft', 'museum_section_id' => $sectionId,
        ]);
        return MuseumDocument::create([
            'museum_entry_id' => $entry->id,
            'label' => 'Музейный документ',
            'file_type' => 'pdf',
            'storage_path' => 'museum/documents/fictional-'.$slug.'.pdf',
            'sha256' => str_repeat('a', 64),
            'size_bytes' => 120,
        ]);
    }

    public function test_editor_cannot_approve_or_download_a_document_outside_assigned_section(): void
    {
        $own = MuseumSection::create([
            'slug' => 'editor-own-docs', 'title' => 'Свой раздел', 'status' => 'published',
        ]);
        $other = MuseumSection::create([
            'slug' => 'editor-other-docs', 'title' => 'Чужой раздел', 'status' => 'published',
        ]);
        $role = MoonshineUserRole::where('name', 'Editor')->firstOrFail();
        $editor = MoonshineUser::factory()->create(['moonshine_user_role_id' => $role->id]);
        $own->editors()->attach($editor->id);

        $mine = $this->document($own->id, 'mine');
        $secret = $this->document($other->id, 'secret');

        $this->actingAs($editor, 'moonshine');
        $this->get(route('museum.documents.download', $secret))->assertForbidden();
        $this->patch(route('museum.documents.accessibility', $secret), [
            'accessibility_reviewed' => true,
            'accessibility_note' => str_repeat('Проверенное описание. ', 4),
        ])->assertForbidden();
        $this->patch(route('museum.documents.accessible-edition', $secret), [
            'source_sha256' => $secret->sha256,
            'accessible_html' => '<p>Фальшивая утверждённая редакция чужого документа</p>',
            'approve_equivalence' => true,
        ])->assertForbidden();
        $this->delete(route('museum.documents.destroy', $secret))->assertForbidden();
        $this->assertNull($secret->fresh()->accessible_reviewed_at);
        $this->assertFalse((bool) $secret->fresh()->accessibility_reviewed);
        $this->assertDatabaseHas('museum_documents', ['id' => $secret->id]);

        $this->patch(route('museum.documents.accessibility', $mine), [
            'accessibility_reviewed' => true,
            'accessibility_note' => str_repeat('Проверенное описание. ', 4),
        ])->assertRedirect();
        $this->assertTrue($mine->fresh()->accessibility_reviewed);
        $this->assertFalse((bool) $secret->fresh()->accessibility_reviewed);
    }
}
