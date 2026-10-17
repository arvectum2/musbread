<?php

namespace Tests\Feature;

use App\Models\MuseumEntry;
use App\Models\MuseumEvent;
use App\Models\MuseumFixedPageSeo;
use App\Models\MuseumSection;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Validation\ValidationException;
use MoonShine\Laravel\Models\MoonshineUser;
use MoonShine\Laravel\Models\MoonshineUserRole;
use Tests\TestCase;

final class MuseumFixedPageSeoTest extends TestCase
{
    use RefreshDatabase;

    private function snapshot(): array
    {
        $out=storage_path('framework/testing/tz185-187-fixed.json');
        $manifest=storage_path('framework/testing/tz185-187-fixed-manifest.json');
        try {
            $this->artisan('museum:export',[
                '--output'=>$out,'--manifest'=>$manifest,
            ])->assertSuccessful();
            $json=json_decode(file_get_contents($out),true,flags:JSON_THROW_ON_ERROR);
            $this->assertSame(hash_file('sha256',$out),
                json_decode(file_get_contents($manifest),true)['files']['published.json']['sha256']);
            return $json;
        } finally {
            @unlink($out);@unlink($manifest);
        }
    }

    public function test_draft_fixed_page_seo_is_private_and_independent_fields_export_only_when_approved(): void
    {
        $this->assertArrayNotHasKey('fixed_page_seo',$this->snapshot());
        $draft=MuseumFixedPageSeo::create([
            'path'=>'/','status'=>'draft','seo_title'=>'Секретный заголовок',
            'seo_description'=>'Секретное описание','h1'=>'Секретный H1',
        ]);
        $published=MuseumFixedPageSeo::create([
            'path'=>'/events/','status'=>'published',
            'seo_title'=>'SEO афиши для посетителя',
            'seo_description'=>'SEO анонсов и событий',
            'h1'=>'Афиша для посетителя',
        ]);
        $another=MuseumFixedPageSeo::create([
            'path'=>'/guide/plan-visit/','status'=>'published',
            'h1'=>'Спланируйте визит',
        ]);
        $data=$this->snapshot();
        $this->assertSame(['/events/','/guide/plan-visit/'],
            array_keys($data['fixed_page_seo']));
        $this->assertSame([
            'h1'=>'Афиша для посетителя',
            'seo_description'=>'SEO анонсов и событий',
            'seo_title'=>'SEO афиши для посетителя',
        ],$data['fixed_page_seo']['/events/']);
        $this->assertSame(['h1'=>'Спланируйте визит'],$data['fixed_page_seo']['/guide/plan-visit/']);
        $this->assertStringNotContainsString('Секрет',json_encode($data,JSON_UNESCAPED_UNICODE));
        $draft->update(['status'=>'published']);
        $this->assertSame('Секретный заголовок',$this->snapshot()['fixed_page_seo']['/']['seo_title']);
        $published->update(['seo_description'=>null]);
        $this->assertArrayNotHasKey('seo_description',$this->snapshot()['fixed_page_seo']['/events/']);
        $another->update(['status'=>'draft']);
        $this->assertArrayNotHasKey('/guide/plan-visit/',$this->snapshot()['fixed_page_seo']);
    }

    public function test_disallow_duplicate_and_fake_content_routes_without_cms_rights(): void
    {
        $allowed=['/','/news/','/museum/','/events/','/search/','/excursions/',
                  '/exhibitions/','/documents/','/guide/museum-contacts/'];
        foreach($allowed as $path) $this->assertTrue(MuseumFixedPageSeo::validFixedPath($path),$path);
        foreach(['/admin/','/admin/museum-media','/events/private/','/news/private/',
                  '/guide/../secret/','/guide/evil?x=1/','https://bad.site/','//site/',
                  '/guide/','/media/abc.webp','/EN/','/guide/foo//','/guide/x/%2f/'] as $path) {
            $this->assertFalse(MuseumFixedPageSeo::validFixedPath($path),$path);
        }
        try {
            MuseumFixedPageSeo::create(['path'=>'/news/private/','status'=>'published','h1'=>'Секрет']);
            $this->fail('Entry SEO must be edited on the original material, not overridden here');
        } catch(ValidationException $expected) {
            $this->assertArrayHasKey('path',$expected->errors());
        }
        $record=MuseumFixedPageSeo::create(['path'=>'/','status'=>'draft','h1'=>'Заголовок']);
        $this->assertNotNull($record->id);
        $this->expectException(\Illuminate\Database\UniqueConstraintViolationException::class);
        MuseumFixedPageSeo::create(['path'=>'/','status'=>'published','h1'=>'Другой заголовок']);
    }

    public function test_fixed_seo_form_and_role_permission_are_admin_only(): void
    {
        $uri='/admin/resource/museum-fixed-page-seo-resource/fixed-page-seo-form-page';
        $this->get($uri)->assertRedirect('/admin/login');
        $editor=MoonshineUser::factory()->create([
            'moonshine_user_role_id'=>MoonshineUserRole::where('name','Editor')->firstOrFail()->id,
        ]);
        $this->actingAs($editor,'moonshine')->get('/admin')->assertOk()
            ->assertDontSee('SEO фиксированных страниц');
        $this->get($uri)->assertForbidden();
        $this->actingAs(MoonshineUser::factory()->create(),'moonshine')
            ->get('/admin')->assertOk()->assertSee('SEO фиксированных страниц');
        $this->get($uri)->assertOk()
            ->assertSee('name="path"',false)->assertSee('name="seo_title"',false)
            ->assertSee('name="seo_description"',false)->assertSee('name="h1"',false);
        $this->get('/admin/resource/museum-entry-resource/museum-entry-form-page')
            ->assertOk()->assertSee('name="h1_en"',false);
    }

    public function test_cms_entry_event_and_section_seo_do_not_get_overridden_by_fixed_route_editor(): void
    {
        MuseumFixedPageSeo::create(['path'=>'/events/','status'=>'published','seo_title'=>'SEO афиши']);
        $entry=MuseumEntry::create([
            'type'=>'news','slug'=>'editor-entry','title'=>'Новость','status'=>'published',
            'published_at'=>now()->subDay(),'body'=>'Опубликованная новость',
            'h1'=>'Новость для читателя','seo_title'=>'SEO новости',
            'seo_description'=>'Описание новости',
            'title_en'=>'English News','h1_en'=>'English custom H1',
            'body_en'=>'English content', 'seo_title_en'=>'EN SEO page',
        ]);
        $event=MuseumEvent::create([
            'slug'=>'editor-event','title'=>'Событие','starts_at'=>'2026-11-02',
            'category'=>'Выставка','body'=>'Описание','excerpt'=>'Анонс события','status'=>'published',
            'published_at'=>now()->subDay(),'seo_title'=>'SEO события','h1'=>'H1 события',
        ]);
        $section=MuseumSection::create([
            'slug'=>'research','title'=>'Наука','status'=>'published',
            'seo_title'=>'SEO раздела','h1'=>'H1 раздела',
        ]);
        $data=$this->snapshot();
        $this->assertSame('SEO новости',$data['entries'][0]['seo_title']);
        $this->assertSame('English custom H1',$data['entries'][0]['translations']['en']['h1']);
        $this->assertSame('SEO события',$data['events'][0]['seo_title']);
        $this->assertSame('H1 раздела',$data['sections'][0]['h1']);
        $this->assertSame('SEO афиши',$data['fixed_page_seo']['/events/']['seo_title']);
        $this->assertArrayNotHasKey('/news/editor-entry/',$data['fixed_page_seo']);
        $this->assertArrayNotHasKey('/events/editor-event/',$data['fixed_page_seo']);
    }
}
