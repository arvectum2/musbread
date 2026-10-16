<?php

declare(strict_types=1);

namespace Tests\Feature;

use App\Models\MuseumEntry;
use App\Models\MuseumMedia;
use App\Models\MuseumSection;
use App\Support\MuseumAltDraft;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Http\UploadedFile;
use Illuminate\Support\Facades\Storage;
use MoonShine\Laravel\Models\MoonshineUser;
use MoonShine\Laravel\Models\MoonshineUserRole;
use Tests\TestCase;

final class MuseumAltDraftTest extends TestCase
{
    use RefreshDatabase;

    public function test_caption_suggestion_is_private_review_required_and_not_persisted(): void
    {
        $entry = MuseumEntry::create(['slug'=>'alt-news','type'=>'news','title'=>'Экспозиция','body'=>'Текст','status'=>'draft']);
        $route = route('museum.media.alt-suggest');
        $payload = ['museum_entry_id'=>$entry->id,'caption'=>'Фотография: старинная русская печь и деревянные лопаты в музее'];
        $this->postJson($route, $payload)->assertUnauthorized();
        $admin=MoonshineUser::factory()->create();
        $this->actingAs($admin,'moonshine');
        $this->postJson($route,$payload)->assertOk()
            ->assertJsonPath('review_required',true)
            ->assertJsonPath('suggestion','Старинная русская печь и деревянные лопаты в музее')
            ->assertHeader('Cache-Control','no-store, private');
        $this->assertDatabaseCount('museum_media',0);
        $this->get('/admin/museum-media')->assertOk()
            ->assertSee('Предложить alt по подписи')
            ->assertSee('требует вашей проверки');
        Storage::fake('local');
        $this->post(route('museum.media.store'),[
            'museum_entry_id'=>$entry->id,'caption'=>$payload['caption'],
            'alt'=>'Старинная русская печь и деревянные лопаты в музее',
            'image'=>UploadedFile::fake()->image('hall.png',40,30),
        ])->assertRedirect(route('museum.media.index'));
        $this->assertSame('Старинная русская печь и деревянные лопаты в музее',MuseumMedia::firstOrFail()->alt);
    }

    public function test_suggestions_reject_generic_text_and_never_infer_unseen_objects(): void
    {
        $draft=app(MuseumAltDraft::class);
        $this->assertSame('Восковые фигуры в витрине зала', $draft->suggest('  Фото:  Восковые фигуры   в витрине зала. '));
        foreach (['Фото', 'IMG_0001', 'Изображение', 'Просто красивое фото',
                  '<script>alert(1)</script>', 'фото: фото'] as $bad) {
            try {
                $draft->suggest($bad);
                $this->fail('Generic alt should not be accepted: '.$bad);
            } catch (\Illuminate\Validation\ValidationException $expected) {
                $this->assertArrayHasKey('caption',$expected->errors());
            }
        }
    }

    public function test_editor_may_not_generate_suggestions_about_foreign_section(): void
    {
        $mine=MuseumSection::create(['slug'=>'mine','title'=>'Мой','status'=>'published']);
        $other=MuseumSection::create(['slug'=>'other','title'=>'Чужой','status'=>'published']);
        $entry=MuseumEntry::create(['slug'=>'foreign-alt','type'=>'news','title'=>'Чужое название','body'=>'Текст','status'=>'draft','museum_section_id'=>$other->id]);
        $role=MoonshineUserRole::where('name','Editor')->firstOrFail();
        $editor=MoonshineUser::factory()->create(['moonshine_user_role_id'=>$role->id]);
        $mine->editors()->attach($editor->id);
        $this->actingAs($editor,'moonshine')->postJson(route('museum.media.alt-suggest'),[
            'museum_entry_id'=>$entry->id,'caption'=>'Старинный амбар и мельничный камень',
        ])->assertForbidden();
        $this->assertDatabaseCount('museum_media',0);
    }
}
