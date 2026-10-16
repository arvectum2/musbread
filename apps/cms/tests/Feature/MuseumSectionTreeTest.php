<?php

namespace Tests\Feature;

use App\Models\MuseumAuditRecord;
use App\Models\MuseumEntry;
use App\Models\MuseumSection;
use Illuminate\Foundation\Testing\RefreshDatabase;
use MoonShine\Laravel\Models\MoonshineUser;
use MoonShine\Laravel\Models\MoonshineUserRole;
use Tests\TestCase;

class MuseumSectionTreeTest extends TestCase
{
    use RefreshDatabase;

    private function section(string $slug, ?int $parent = null, string $status = 'published', int $order = 0): MuseumSection
    {
        return MuseumSection::create([
            'slug' => $slug, 'title' => 'Раздел '.$slug,
            'parent_id' => $parent, 'status' => $status, 'sort_order' => $order,
        ]);
    }

    private function editor(): MoonshineUser
    {
        $role = MoonshineUserRole::query()->where('name', 'Editor')->firstOrFail();
        return MoonshineUser::factory()->create(['moonshine_user_role_id' => $role->id]);
    }

    public function test_private_tree_redirects_guest_and_denies_editor(): void
    {
        $section = $this->section('secret-section');
        $this->get(route('museum.sections.tree'))->assertRedirect('/admin/login')
            ->assertDontSee('secret-section');
        $this->post(route('museum.sections.reorder', ['section' => $section->id]), [
            'direction' => 'down',
        ])->assertRedirect('/admin/login');
        $this->actingAs($this->editor(), 'moonshine');
        $this->get(route('museum.sections.tree'))->assertForbidden()->assertDontSee('secret-section');
        $this->post(route('museum.sections.reorder', ['section' => $section->id]), [
            'direction' => 'down',
        ])->assertForbidden();
    }

    public function test_empty_tree_and_admin_entry_point(): void
    {
        $this->actingAs(MoonshineUser::factory()->create(), 'moonshine');
        $this->get(route('museum.sections.tree'))->assertOk()
            ->assertSee('Разделы ещё не созданы')
            ->assertHeader('X-Robots-Tag', 'noindex, nofollow, noarchive')
            ->assertHeader('Cache-Control', 'max-age=0, no-store, private')
            ->assertHeader('Content-Security-Policy', "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; base-uri 'none'; frame-ancestors 'none'");
        $this->section('example');
        $this->get('/admin/resource/museum-section-resource/museum-section-index-page')
            ->assertOk()->assertSee('Открыть карту');
    }

    public function test_hierarchy_shows_true_effective_publication_state_and_counts(): void
    {
        $root = $this->section('open-root', null, 'published', 2);
        $child = $this->section('open-child', $root->id, 'published', 1);
        $draft = $this->section('closed-parent', null, 'draft', 1);
        $blocked = $this->section('closed-child', $draft->id, 'published', 3);
        MuseumEntry::create(['slug' => 'published-child', 'title' => 'Готово',
            'type' => 'page', 'body' => 'Текст', 'museum_section_id' => $child->id,
            'status' => 'published', 'published_at' => now()->subDay()]);
        MuseumEntry::create(['slug' => 'future-child', 'title' => 'Отложено',
            'type' => 'page', 'body' => 'Текст', 'museum_section_id' => $child->id,
            'status' => 'published', 'published_at' => now()->addDay()]);
        MuseumEntry::create(['slug' => 'blocked-story', 'title' => 'Блокировано',
            'type' => 'page', 'body' => 'Текст', 'museum_section_id' => $blocked->id,
            'status' => 'published', 'published_at' => now()->subDay()]);
        $this->actingAs(MoonshineUser::factory()->create(), 'moonshine');
        $response = $this->get(route('museum.sections.tree'))->assertOk()
            ->assertSee('Всего разделов:')
            ->assertSee('Скрыт неопубликованным предком')
            ->assertSee('Публикуемых материалов:')
            ->assertSee('Назначенных редакторов:')
            ->assertDontSee('blocked-story'); // names of entries never leave summary
        $html = $response->getContent();
        $this->assertLessThan(strpos($html, 'data-section="open-child"'), strpos($html, 'data-section="open-root"'));
        $this->assertLessThan(strpos($html, 'data-section="closed-child"'), strpos($html, 'data-section="closed-parent"'));
        $this->assertMatchesRegularExpression('/data-section="open-child"[^>]*>.*?Публикуемых: 1/s', $html);
        $this->assertMatchesRegularExpression('/data-section="closed-child"[^>]*>.*?Публикуемых: 0/s', $html);
    }

    public function test_parent_selector_omits_self_and_descendants_but_shows_other_branches(): void
    {
        $root = $this->section('root');
        $child = $this->section('child', $root->id);
        $grandchild = $this->section('grandchild', $child->id);
        $other = $this->section('available-root');
        $this->actingAs(MoonshineUser::factory()->create(), 'moonshine');

        $response = $this->get('/admin/resource/museum-section-resource/museum-section-form-page/'.$root->id)
            ->assertOk();
        $body = $response->getContent();
        $this->assertSame(1, preg_match('/<select\b[^>]*name="parent_id"[^>]*>(.*?)<\/select>/s', $body, $parentSelect));
        preg_match_all('/<option\b[^>]*\bvalue="(\d+)"/s', $parentSelect[1], $found);
        $optionIds = array_map('intval', $found[1]);
        $this->assertNotContains($root->id, $optionIds);
        $this->assertNotContains($child->id, $optionIds);
        $this->assertNotContains($grandchild->id, $optionIds);
        $this->assertContains($other->id, $optionIds);
        $this->get('/admin/resource/museum-section-resource/museum-section-form-page/'.$child->id)
            ->assertOk()->assertSee('Раздел root');
    }

    public function test_reorder_stably_changes_only_siblings_and_tracks_model_audit(): void
    {
        $root = $this->section('root');
        $otherRoot = $this->section('other-root');
        $a = $this->section('alpha', $root->id, 'published', 0);
        $b = $this->section('beta', $root->id, 'draft', 0);
        $c = $this->section('gamma', $root->id, 'published', 11);
        $untouched = $this->section('unrelated', $otherRoot->id, 'published', 31);
        $this->actingAs(MoonshineUser::factory()->create(), 'moonshine');
        $this->post(route('museum.sections.reorder', ['section' => $b->id]), [
            'direction' => 'up',
        ])->assertRedirect(route('museum.sections.tree'));
        $this->assertSame(0, $b->fresh()->sort_order);
        $this->assertSame(1, $a->fresh()->sort_order);
        $this->assertSame(2, $c->fresh()->sort_order);
        $this->assertSame(31, $untouched->fresh()->sort_order);
        $this->assertSame('draft', $b->fresh()->status);
        $this->assertDatabaseHas('museum_audit_records', [
            'subject_type' => 'MuseumSection', 'subject_id' => $a->id, 'action' => 'updated',
        ]);
        $this->post(route('museum.sections.reorder', ['section' => $b->id]), [
            'direction' => 'down',
        ])->assertRedirect();
        $this->assertSame(0, $a->fresh()->sort_order);
        $this->assertSame(1, $b->fresh()->sort_order);
    }

    public function test_boundary_invalid_direction_and_missing_id_do_not_modify_data(): void
    {
        $a = $this->section('first', null, 'published', 5);
        $b = $this->section('second', null, 'published', 7);
        $this->actingAs(MoonshineUser::factory()->create(), 'moonshine');
        $url = route('museum.sections.reorder', ['section' => $a->id]);
        $this->post($url, ['direction' => 'sideways'])->assertSessionHasErrors('direction');
        $this->post($url, [])->assertSessionHasErrors('direction');
        $this->post($url, ['direction' => 'up'])->assertSessionHasErrors('direction');
        $this->post(route('museum.sections.reorder', ['section' => $b->id]), [
            'direction' => 'down',
        ])->assertSessionHasErrors('direction');
        $this->post('/admin/museum-sections/not-an-id/reorder', ['direction' => 'up'])->assertNotFound();
        $this->post('/admin/museum-sections/999999/reorder', ['direction' => 'up'])->assertNotFound();
        $this->assertSame(5, $a->fresh()->sort_order);
        $this->assertSame(7, $b->fresh()->sort_order);
    }
}
