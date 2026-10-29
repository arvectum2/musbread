<?php
declare(strict_types=1);
namespace Tests\Feature;
use App\Models\MuseumInboundRequest;
use Illuminate\Foundation\Testing\RefreshDatabase;
use MoonShine\Laravel\Models\MoonshineUser;
use MoonShine\Laravel\Models\MoonshineUserRole;
use Tests\TestCase;

final class MuseumInboundAccessTest extends TestCase {
    use RefreshDatabase;

    public function test_private_inbox_only_visible_to_superuser_and_not_public(): void {
        $row=MuseumInboundRequest::create([
            'external_id'=>str_repeat('a',32), 'kind'=>'feedback',
            'payload'=>['kind'=>'feedback','name'=>'Тестовое имя','email'=>'test@example.org',
                'message'=>'Закрытый вопрос','consent'=>'test-v1'],
        ]);
        $path='/admin/resource/museum-inbound-request-resource/inbox-detail-page/'.$row->id;
        $this->get($path)->assertRedirect();
        $editorRole=MoonshineUserRole::where('name','Editor')->firstOrFail();
        $editor=MoonshineUser::factory()->create(['moonshine_user_role_id'=>$editorRole->id]);
        $this->actingAs($editor,'moonshine')->get($path)->assertForbidden();
        $admin=MoonshineUser::factory()->create();
        $this->actingAs($admin,'moonshine')->get($path)->assertOk()
            ->assertSee('Тестовое имя')->assertSee('Закрытый вопрос');
        // The indexed list must never contain decrypted contact/message fields.
        $this->get('/admin/resource/museum-inbound-request-resource/inbox-index-page')
            ->assertOk()->assertDontSee('test@example.org')->assertDontSee('Закрытый вопрос');
    }
}
