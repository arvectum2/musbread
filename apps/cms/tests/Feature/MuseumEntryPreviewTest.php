<?php

namespace Tests\Feature;

use App\Models\MuseumEntry;
use App\Models\MuseumSection;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\DB;
use MoonShine\Laravel\Models\MoonshineUser;
use MoonShine\Laravel\Models\MoonshineUserRole;
use Tests\TestCase;

class MuseumEntryPreviewTest extends TestCase
{
    use RefreshDatabase;

    private function entry(string $slug, ?int $sectionId = null): MuseumEntry
    {
        return MuseumEntry::create([
            'type' => 'news', 'slug' => $slug, 'title' => 'Пример музейной новости',
            'h1' => 'Заголовок будущего материала', 'body' => '<p>Содержание черновика</p>',
            'status' => 'draft', 'museum_section_id' => $sectionId,
        ]);
    }

    public function test_guest_is_redirected_without_receiving_draft_content(): void
    {
        $entry = $this->entry('hidden-preview');
        $this->get(route('museum.entries.preview', $entry->id))
            ->assertRedirect('/admin/login')->assertDontSee('Содержание черновика');
    }

    public function test_admin_previews_draft_and_scheduled_record_with_private_headers(): void
    {
        $draft = $this->entry('unpublished-story');
        $this->actingAs(MoonshineUser::factory()->create(), 'moonshine');
        $url = route('museum.entries.preview', $draft->id);
        $this->get($url)->assertOk()
            ->assertSee('Черновик')->assertSee('Содержание черновика')
            ->assertSee('сохранённая версия')
            ->assertHeader('X-Robots-Tag', 'noindex, nofollow, noarchive')
            ->assertHeader('Cache-Control', 'max-age=0, no-store, private')
            ->assertHeader('Referrer-Policy', 'no-referrer')
            ->assertHeader('X-Frame-Options', 'DENY');
        $this->get('/admin/resource/museum-entry-resource/museum-entry-index-page')
            ->assertOk()->assertSee($url, false);

        $draft->update(['status' => 'published', 'published_at' => now()->addDay()]);
        $this->assertFalse($draft->newQuery()->public()->whereKey($draft->id)->exists());
        $this->get($url)->assertOk()
            ->assertSee('Помечен к публикации')->assertSee('Содержание черновика');
    }

    public function test_editor_cannot_guess_other_sections_or_unassigned_drafts(): void
    {
        $mine = MuseumSection::create(['slug' => 'owned-section', 'title' => 'Своя рубрика', 'status' => 'published']);
        $other = MuseumSection::create(['slug' => 'other-section', 'title' => 'Чужая рубрика', 'status' => 'published']);
        $ownDraft = $this->entry('my-draft', $mine->id);
        $otherDraft = $this->entry('other-draft', $other->id);
        $unassigned = $this->entry('unassigned-draft');
        $role = MoonshineUserRole::query()->firstOrCreate(['name' => 'Editor']);
        $editor = MoonshineUser::factory()->create(['moonshine_user_role_id' => $role->id]);
        $mine->editors()->attach($editor->id);
        $this->actingAs($editor, 'moonshine');

        $this->get(route('museum.entries.preview', $ownDraft->id))->assertOk();
        $this->get(route('museum.entries.preview', $otherDraft->id))
            ->assertNotFound()->assertDontSee('Чужая рубрика');
        $this->get(route('museum.entries.preview', $unassigned->id))->assertNotFound();
        $this->get('/admin/museum-entries/not-a-number/preview')->assertNotFound();
        $this->get('/admin/museum-entries/99999/preview')->assertNotFound();
    }

    public function test_preview_sanitizes_corrupted_html_again_and_escapes_headings(): void
    {
        $draft = $this->entry('unsafe-html');
        DB::table('museum_entries')->where('id', $draft->id)->update([
            'h1' => '<img src=x onerror=alert(9)>',
            'body' => '<p>Допустимое содержимое</p><script>alert(1)</script>'
                . '<a href="javascript:alert(2)" onclick="alert(3)">Тест</a>',
        ]);
        $this->actingAs(MoonshineUser::factory()->create(), 'moonshine')
            ->get(route('museum.entries.preview', $draft->id))
            ->assertOk()->assertSee('<p>Допустимое содержимое</p>', false)
            ->assertSee('&lt;img src=x onerror=alert(9)&gt;', false)
            ->assertDontSee('<script', false)
            ->assertDontSee('href="javascript:', false)
            ->assertDontSee('onclick=', false)
            ->assertHeader('Content-Security-Policy', "default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; object-src 'none'; form-action 'none'; frame-ancestors 'none'");
    }
}
