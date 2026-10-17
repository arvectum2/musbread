<?php
namespace Tests\Feature;

use App\Models\MuseumEntry;
use App\Models\MuseumEvent;
use App\Models\MuseumSection;
use Illuminate\Foundation\Testing\RefreshDatabase;
use MoonShine\Laravel\Models\MoonshineUser;
use MoonShine\Laravel\Models\MoonshineUserRole;
use Tests\TestCase;

class MuseumContextLinksTest extends TestCase
{
    use RefreshDatabase;

    private function entry(string $slug,string $status='published',?int $section=null):MuseumEntry {
        return MuseumEntry::create([
            'type'=>'news','slug'=>$slug,'title'=>'Статья '.$slug,
            'body'=>'Официальный текст тестового материала','status'=>$status,
            'museum_section_id'=>$section,
        ]);
    }
    private function event(string $slug,string $status='published',?int $section=null):MuseumEvent {
        return MuseumEvent::create([
            'slug'=>$slug,'title'=>'Событие '.$slug,'status'=>$status,
            'starts_at'=>'2026-11-17','category'=>'Тестовое','excerpt'=>'Описание',
            'body'=>'Текст','museum_section_id'=>$section,
        ]);
    }
    public function test_guest_cannot_access_read_only_link_catalog():void {
        $this->entry('private-draft','draft');
        $this->get(route('museum.content.links'))->assertRedirect('/admin/login')
            ->assertDontSee('private-draft')
            ->assertDontSee('Внутренняя ссылка');
    }
    public function test_catalog_uses_export_eligibility_and_does_not_leak_hidden_or_future_names():void {
        $this->entry('public-article');
        $this->event('public-event');
        $this->entry('draft-secret','draft');
        $this->event('draft-event','draft');
        $hidden=MuseumSection::create(['slug'=>'hidden-section','title'=>'Тайный раздел','status'=>'draft']);
        $this->entry('hidden-article','published',$hidden->id);
        $future=$this->entry('future-article');
        $future->update(['published_at'=>now()->addDay()]);
        $expired=$this->entry('expired-article');
        $expired->update(['unpublish_at'=>now()->subMinute()]);
        $en=$this->entry('translated-article');
        $en->update(['title_en'=>'Approved English article','body_en'=>'Published English body']);
        $partial=$this->entry('english-draft');
        $partial->update(['title_en'=>'SECRET English title','body_en'=>null]);
        $admin=MoonshineUser::factory()->create();
        $response=$this->actingAs($admin,'moonshine')->get(route('museum.content.links'))->assertOk()
            ->assertHeader('Cache-Control','max-age=0, no-store, private')
            ->assertHeader('X-Robots-Tag','noindex, nofollow, noarchive')
            ->assertHeader('X-Frame-Options','DENY')
            ->assertSee('/news/public-article/',false)
            ->assertSee('/events/public-event/',false)
            ->assertSee('/en/news/translated-article/',false)
            ->assertSee('Approved English article'); // HTML has no write form
        foreach(['draft-secret','draft-event','hidden-article','future-article','expired-article',
                'SECRET English title'] as $hiddenSlug) {
            $response->assertDontSee($hiddenSlug);
        }
        $response->assertDontSee('<form',false);
        $this->assertSame(7,MuseumEntry::count()); // no mutation by picker
    }
    public function test_role_limited_editor_only_sees_published_targets_not_drafts():void {
        $this->entry('visible-to-editor');
        $this->entry('private-secret','draft');
        $role=MoonshineUserRole::query()->where('name','Editor')->firstOrFail();
        $editor=MoonshineUser::factory()->create(['moonshine_user_role_id'=>$role->id]);
        $this->actingAs($editor,'moonshine')->get(route('museum.content.links'))
            ->assertOk()->assertSee('/news/visible-to-editor/',false)
            ->assertDontSee('private-secret');
        $this->get('/admin')->assertOk()->assertSee('Подобрать ссылку в текст');
    }
}
