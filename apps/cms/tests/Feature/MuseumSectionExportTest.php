<?php

namespace Tests\Feature;

use App\Models\MuseumEntry;
use App\Models\MuseumSection;
use Database\Seeders\ReferenceMuseumSectionsSeeder;
use Illuminate\Foundation\Testing\RefreshDatabase;
use MoonShine\Laravel\Models\MoonshineUser;
use Tests\TestCase;

class MuseumSectionExportTest extends TestCase
{
    use RefreshDatabase;

    public function test_opt_in_reference_seed_populates_seven_roots_and_fifty_five_children_idempotently(): void
    {
        $this->seed(ReferenceMuseumSectionsSeeder::class);
        $this->assertSame(62, MuseumSection::count());
        $this->assertSame(7, MuseumSection::whereNull('parent_id')->count());
        $firstId = MuseumSection::where('slug', 'museum')->value('id');
        $museum = MuseumSection::findOrFail($firstId);
        $museum->update(['title' => 'Редактор переименовал раздел']);
        $this->seed(ReferenceMuseumSectionsSeeder::class);
        $this->assertSame(62, MuseumSection::count());
        $this->assertSame($firstId, MuseumSection::where('slug', 'museum')->value('id'));
        $this->assertSame('Редактор переименовал раздел', $museum->fresh()->title);
    }

    private function export(string $suffix): array
    {
        $output = storage_path('framework/testing/section-'.$suffix.'.json');
        $manifest = storage_path('framework/testing/section-'.$suffix.'-manifest.json');
        try {
            $this->artisan('museum:export', [
                '--output' => $output,
                '--manifest' => $manifest,
            ])->assertSuccessful();
            $snapshot = json_decode(file_get_contents($output), true, flags: JSON_THROW_ON_ERROR);
            $audit = json_decode(file_get_contents($manifest), true, flags: JSON_THROW_ON_ERROR);
            $this->assertSame(hash_file('sha256', $output), $audit['files']['published.json']['sha256']);
            return [$snapshot, $audit];
        } finally {
            @unlink($output);
            @unlink($manifest);
        }
    }

    public function test_reference_sections_are_in_cms_snapshot_but_no_editor_grants_or_drafts_leak(): void
    {
        $this->seed(ReferenceMuseumSectionsSeeder::class);
        $section = MuseumSection::where('slug', 'museum')->firstOrFail();
        $editor = MoonshineUser::factory()->create();
        $section->editors()->attach($editor->id);
        [$snapshot, $audit] = $this->export('reference');
        $this->assertCount(62, $snapshot['sections']);
        $this->assertSame(62, $audit['section_count']);
        $this->assertSame('museum', $snapshot['sections'][0]['slug']);
        $text = json_encode($snapshot, JSON_UNESCAPED_UNICODE);
        $this->assertStringNotContainsString('moonshine_user_id', $text);
        $this->assertStringNotContainsString($editor->email, $text);
        $this->assertStringNotContainsString('editors', $text);
    }

    public function test_draft_ancestor_excludes_its_children_and_linked_entries(): void
    {
        $root = MuseumSection::create(['slug' => 'root', 'title' => 'Корневой', 'status' => 'draft']);
        $child = MuseumSection::create([
            'slug' => 'child', 'title' => 'Дочерний',
            'status' => 'published', 'parent_id' => $root->id,
        ]);
        $public = MuseumSection::create([
            'slug' => 'published-root', 'title' => 'Открытый',
            'status' => 'published',
        ]);
        MuseumEntry::create([
            'type' => 'page', 'slug' => 'leak', 'title' => 'Не должно утечь',
            'body' => 'Секретный материал', 'status' => 'published',
            'museum_section_id' => $child->id,
        ]);
        MuseumEntry::create([
            'type' => 'page', 'slug' => 'safe', 'title' => 'Открытый материал',
            'body' => 'Публичный текст', 'status' => 'published',
            'museum_section_id' => $public->id,
        ]);
        [$snapshot, $audit] = $this->export('ancestors');
        $this->assertSame(['published-root'], array_column($snapshot['sections'], 'slug'));
        $this->assertSame(['safe'], array_column($snapshot['entries'], 'slug'));
        $this->assertSame('published-root', $snapshot['entries'][0]['section_slug']);
        $this->assertSame(1, $audit['section_count']);
    }

    public function test_new_pages_added_to_existing_section_are_exported_with_assignment_and_hidden_with_draft_ancestor(): void
    {
        $root = MuseumSection::create(['slug'=>'exhibitions-root','title'=>'Выставки','status'=>'published']);
        $child = MuseumSection::create(['slug'=>'exhibitions-child','title'=>'Тематические выставки','status'=>'published','parent_id'=>$root->id]);
        $live = MuseumEntry::create([
            'type'=>'page','slug'=>'new-exhibit-page','title'=>'Новая страница раздела',
            'body'=>'Содержимое страницы','status'=>'published','museum_section_id'=>$child->id,
        ]);
        MuseumEntry::create([
            'type'=>'page','slug'=>'draft-exhibit-page','title'=>'Черновик',
            'body'=>'Не публиковать','status'=>'draft','museum_section_id'=>$child->id,
        ]);
        [$snapshot] = $this->export('new-page-in-section');
        $this->assertSame(['new-exhibit-page'],array_column($snapshot['entries'],'slug'));
        $this->assertSame('exhibitions-child',$snapshot['entries'][0]['section_slug']);
        $this->assertSame('exhibitions-root',$snapshot['sections'][1]['parent_slug']);
        $child->update(['status'=>'draft']);
        [$hidden] = $this->export('hidden-page-in-section');
        $this->assertSame([], $hidden['entries']);
        $this->assertSame(['exhibitions-root'],array_column($hidden['sections'],'slug'));
        $child->update(['status'=>'published']);
        $live->update(['museum_section_id'=>$root->id]);
        [$moved] = $this->export('moved-page-between-sections');
        $this->assertSame('exhibitions-root',$moved['entries'][0]['section_slug']);
    }

    public function test_reorder_and_rename_are_reflected_in_next_snapshot(): void
    {
        $root = MuseumSection::create([
            'slug' => 'visitors', 'title' => 'Посетителям', 'status' => 'published',
        ]);
        $first = MuseumSection::create([
            'slug' => 'prices', 'title' => 'Стоимость',
            'status' => 'published', 'parent_id' => $root->id, 'sort_order' => 10,
        ]);
        $second = MuseumSection::create([
            'slug' => 'access', 'title' => 'Доступная среда',
            'status' => 'published', 'parent_id' => $root->id, 'sort_order' => 20,
        ]);
        $second->update(['title' => 'Доступность музея', 'sort_order' => 2]);
        [$snapshot] = $this->export('sorted');
        $this->assertSame(['visitors', 'access', 'prices'], array_column($snapshot['sections'], 'slug'));
        $this->assertSame('Доступность музея', $snapshot['sections'][1]['title']);
        $this->assertSame('visitors', $snapshot['sections'][1]['parent_slug']);
        $this->assertSame(10, $first->fresh()->sort_order);
    }
}
