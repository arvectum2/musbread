<?php

namespace Tests\Feature;

use App\Models\MuseumEntry;
use App\Models\MuseumSection;
use Illuminate\Foundation\Testing\RefreshDatabase;
use MoonShine\Laravel\Models\MoonshineUser;
use Tests\TestCase;

class MuseumEntryEditorTest extends TestCase
{
    use RefreshDatabase;

    public function test_authenticated_admin_can_create_page_through_moonshine(): void
    {
        $this->actingAs(MoonshineUser::factory()->create(), 'moonshine')
            ->get('/admin/resource/museum-entry-resource/museum-entry-form-page')
            ->assertOk();

        $this->post('/admin/resource/museum-entry-resource/crud', [
            'type' => 'page', 'title' => 'История музея', 'slug' => 'museum-history',
            'body' => 'Предварительный материал', 'status' => 'draft',
            'seo_title' => 'История музея — тест',
        ])->assertRedirect();

        $this->assertDatabaseHas('museum_entries', [
            'type' => 'page', 'slug' => 'museum-history', 'status' => 'draft',
            'seo_title' => 'История музея — тест',
        ]);
        $this->assertSame(0, MuseumEntry::public()->count());
    }

    public function test_editor_creates_page_via_moonshine_in_granted_existing_section(): void
    {
        $root = MuseumSection::create(['slug'=>'catalog','title'=>'Каталог','status'=>'published']);
        $leaf = MuseumSection::create([
            'slug'=>'heritage','title'=>'Наследие','parent_id'=>$root->id,'status'=>'published',
        ]);
        $role = \MoonShine\Laravel\Models\MoonshineUserRole::query()->where('name','Editor')->firstOrFail();
        $editor = MoonshineUser::factory()->create(['moonshine_user_role_id'=>$role->id]);
        $leaf->editors()->attach($editor->id);
        $this->actingAs($editor,'moonshine')
            ->get('/admin/resource/museum-entry-resource/museum-entry-form-page')
            ->assertOk()->assertSee('Наследие');
        $this->post('/admin/resource/museum-entry-resource/crud', [
            'type'=>'page','slug'=>'new-catalog-page','title'=>'Новая страница каталога',
            'museum_section_id'=>$leaf->id,
            'body'=>'Описание из редактора','status'=>'published',
        ])->assertRedirect();
        $created = MuseumEntry::where('slug','new-catalog-page')->firstOrFail();
        $this->assertSame($leaf->id,$created->museum_section_id);
        $this->assertSame('published',$created->status);
    }

    public function test_sql_injection_like_slug_is_rejected_before_persistence(): void
    {
        $this->actingAs(MoonshineUser::factory()->create(), 'moonshine')
            ->post('/admin/resource/museum-entry-resource/crud', [
                'type' => 'news',
                'title' => 'SQL injection smoke',
                'slug' => "x' OR 1=1--",
                'body' => 'Placeholder',
                'status' => 'draft',
            ])->assertRedirect();

        $this->assertSame(0, MuseumEntry::count());
    }

    public function test_invalid_type_cannot_be_published_from_moonshine(): void
    {
        $this->actingAs(MoonshineUser::factory()->create(), 'moonshine')
            ->post('/admin/resource/museum-entry-resource/crud', [
                'type' => 'unknown', 'title' => 'Ошибка', 'slug' => 'invalid',
                'body' => 'Тест', 'status' => 'published',
            ])->assertRedirect();
        $this->assertSame(0, MuseumEntry::count());
    }
}
