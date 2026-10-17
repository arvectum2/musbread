<?php

namespace Tests\Feature;

use App\Models\MuseumEntry;
use App\Models\MuseumEvent;
use App\Models\MuseumSection;
use Illuminate\Foundation\Testing\RefreshDatabase;
use MoonShine\Laravel\Models\MoonshineUser;
use MoonShine\Laravel\Models\MoonshineUserRole;
use Tests\TestCase;

class MuseumSeoEditorFlowTest extends TestCase
{
    use RefreshDatabase;

    public function test_event_and_section_seo_survive_public_export_without_leaking_drafts(): void
    {
        $section = MuseumSection::create([
            'title'=>'Музейные новости', 'slug'=>'news-archive', 'status'=>'published',
            'h1'=>'Важные новости Музея хлеба',
            'seo_title'=>'Новости и выставки — SEO',
            'seo_description'=>'Утверждённое редакционное описание раздела',
        ]);
        MuseumSection::create([
            'title'=>'Скрытые новости', 'slug'=>'news-hidden', 'status'=>'draft',
            'seo_title'=>'Секретный заголовок раздела',
        ]);
        MuseumEvent::create([
            'title'=>'День ремёсел', 'slug'=>'museum-crafts-day', 'category'=>'Мастер-класс',
            'museum_section_id'=>$section->id, 'starts_at'=>'2026-11-21',
            'status'=>'published', 'published_at'=>now()->subDay(),
            'excerpt'=>'Тест', 'body'=>'Тестовая программа',
            'h1'=>'День ремёсел в музее',
            'seo_title'=>'Календарь мастер-классов — SEO',
            'seo_description'=>'Описание события для поисковой системы',
        ]);
        MuseumEvent::create([
            'title'=>'Закрытый анонс', 'slug'=>'hidden-news-event', 'category'=>'Мастер-класс',
            'status'=>'draft', 'starts_at'=>'2026-11-21',
            'excerpt'=>'Тест', 'body'=>'Тест',
            'seo_title'=>'Секретное SEO события',
        ]);
        $out = storage_path('framework/testing/tz233-seo.json');
        $manifest = storage_path('framework/testing/tz233-seo-manifest.json');
        try {
            $this->artisan('museum:export', ['--output'=>$out, '--manifest'=>$manifest])->assertSuccessful();
            $json = json_decode(file_get_contents($out), true, flags: JSON_THROW_ON_ERROR);
            $this->assertSame('Новости и выставки — SEO', $json['sections'][0]['seo_title']);
            $this->assertSame('Важные новости Музея хлеба', $json['sections'][0]['h1']);
            $this->assertSame('Утверждённое редакционное описание раздела', $json['sections'][0]['seo_description']);
            $this->assertSame('Календарь мастер-классов — SEO', $json['events'][0]['seo_title']);
            $this->assertSame('День ремёсел в музее', $json['events'][0]['h1']);
            $this->assertSame('Описание события для поисковой системы', $json['events'][0]['seo_description']);
            $this->assertStringNotContainsString('Секретный', file_get_contents($out));
            $this->assertSame(hash_file('sha256',$out),
                json_decode(file_get_contents($manifest),true)['files']['published.json']['sha256']);
        } finally {
            @unlink($out); @unlink($manifest);
        }
    }

    public function test_editor_sees_daily_tools_but_not_admin_or_demo_menu_items(): void
    {
        $role = MoonshineUserRole::query()->where('name','Editor')->firstOrFail();
        $editor = MoonshineUser::factory()->create(['moonshine_user_role_id'=>$role->id]);
        $this->actingAs($editor,'moonshine')->get('/admin')
            ->assertOk()
            ->assertSee('Материалы и новости')
            ->assertSee('Афиша и мероприятия')
            ->assertSee('Проверить перед публикацией')
            ->assertDontSee('Обращения (демо)')
            ->assertDontSee('История обращений')
            ->assertDontSee('Журнал изменений')
            ->assertDontSee('Статистика действий')
            ->assertDontSee('Карта разделов')
            ->assertDontSee('Запуски публикации');
        $this->actingAs(MoonshineUser::factory()->create(),'moonshine')
            ->get('/admin')->assertOk()
            ->assertSee('Карта разделов')->assertSee('Обращения (демо)')
            ->assertSee('Статистика действий')->assertSee('Запуски публикации');
    }

    public function test_seo_fields_exist_on_existing_moonshine_forms_and_remain_private(): void
    {
        $this->actingAs(MoonshineUser::factory()->create(),'moonshine');
        $this->get('/admin/resource/museum-entry-resource/museum-entry-form-page')
            ->assertOk()->assertSee('name="h1"',false)->assertSee('name="seo_title"',false)
            ->assertSee('name="seo_description"',false);
        $this->get('/admin/resource/museum-event-resource/museum-event-form-page')
            ->assertOk()->assertSee('name="h1"',false)->assertSee('name="seo_title"',false)
            ->assertSee('name="seo_description"',false);
        $this->get('/admin/resource/museum-section-resource/museum-section-form-page')
            ->assertOk()->assertSee('name="h1"',false)->assertSee('name="seo_title"',false)
            ->assertSee('name="seo_description"',false);
    }
}
