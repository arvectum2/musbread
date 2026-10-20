<?php

namespace Tests\Feature;

use App\Models\MuseumEntry;
use Illuminate\Foundation\Testing\RefreshDatabase;
use MoonShine\Laravel\Models\MoonshineUser;
use Tests\TestCase;

final class MuseumEditorMobileUXTest extends TestCase
{
    use RefreshDatabase;

    private function entry(): MuseumEntry
    {
        return MuseumEntry::create([
            'type' => 'news',
            'slug' => 'editor-ux-synthetic',
            'title' => 'Синтетический материал редактора',
            'body' => '<p>Проверка навигации и доступности.</p>',
            'status' => 'draft',
        ]);
    }

    public function test_editor_accessible_names_zoom_and_reusable_ui_assets(): void
    {
        $this->actingAs(MoonshineUser::factory()->create(), 'moonshine');
        $entry = $this->entry();
        $this->get('/admin/resource/museum-entry-resource/museum-entry-form-page/'.$entry->id)
            ->assertOk()
            ->assertSee('name="viewport"', false)
            ->assertDontSee('user-scalable=no', false)
            ->assertSee('Открыть или закрыть', false)
            ->assertSee('museum-cms-accessibility.js')
            ->assertSee('museum-cms-accessibility.css')
            ->assertSee('Маршрут редактора');
    }

    public function test_upload_error_messages_explain_the_next_action_in_russian(): void
    {
        $this->actingAs(MoonshineUser::factory()->create(), 'moonshine');
        $entry = $this->entry();
        $media = route('museum.media.index', ['entry' => $entry->id]);
        $docs = route('museum.documents.index', ['entry' => $entry->id]);
        $this->from($media)->post(route('museum.media.store', ['entry' => $entry->id]), [
            'museum_entry_id' => $entry->id,
        ])->assertRedirect($media)->assertSessionHasErrors(['alt', 'image']);
        $this->assertStringContainsString('Опишите, что видно',
            session('errors')->first('alt'));
        $this->assertStringContainsString('Выберите изображение',
            session('errors')->first('image'));

        $this->from($docs)->post(route('museum.documents.store', ['entry' => $entry->id]), [
            'museum_entry_id' => $entry->id,
        ])->assertRedirect($docs)->assertSessionHasErrors(['label', 'document']);
        $this->assertStringContainsString('Укажите понятное название',
            session('errors')->first('label'));
        $this->assertStringContainsString('Выберите документ',
            session('errors')->first('document'));
        $this->assertDatabaseCount('museum_media', 0);
        $this->assertDatabaseCount('museum_documents', 0);
    }

    public function test_preview_navigation_returns_to_entry_and_private_media(): void
    {
        $this->actingAs(MoonshineUser::factory()->create(), 'moonshine');
        $entry = $this->entry();
        $this->get(route('museum.entries.preview', ['entry' => $entry->id]))
            ->assertOk()
            ->assertSee('Вернуться к редактированию материала')
            ->assertSee(route('museum.media.index', ['entry' => $entry->id]), false)
            ->assertSee(route('museum.documents.index', ['entry' => $entry->id]), false)
            ->assertSee('не публикует материал');
    }

    public function test_documents_table_has_keyboard_scroll_region_even_when_empty(): void
    {
        $this->actingAs(MoonshineUser::factory()->create(), 'moonshine');
        $this->get(route('museum.documents.index'))->assertOk()
            ->assertSee('role="region"', false)
            ->assertSee('aria-label="Таблица загруженных документов"', false)
            ->assertSee('tabindex="0"', false)
            ->assertSee('стрелки вправо или влево');
    }

    public function test_preflight_names_queue_action_without_suggesting_live_deployment(): void
    {
        $this->actingAs(MoonshineUser::factory()->create(), 'moonshine');
        config([
            'museum.queue_publication' => true,
            'museum.editorial_approval_queue' => false,
            'queue.default' => 'database',
            'cache.default' => 'database',
        ]);
        $this->get(route('museum.content.preflight'))->assertOk()
            ->assertSee('Подготовка закрытой выгрузки')
            ->assertSee('Сформировать закрытый пакет (не публикует сайт)')
            ->assertDontSee('Опубликовать — подготовить пакет в очереди');
    }
}
