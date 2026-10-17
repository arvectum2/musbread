<?php
namespace Tests\Feature;
use App\Models\MuseumVisitorContacts;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Validation\ValidationException;
use MoonShine\Laravel\Models\MoonshineUser;
use MoonShine\Laravel\Models\MoonshineUserRole;
use Tests\TestCase;

final class MuseumVisitorContactsTest extends TestCase {
    use RefreshDatabase;
    private function approved():array {
        return [
            'scope'=>'primary','status'=>'published',
            'address'=>'QA: ул. Музейная, д. 17 (только тест)',
            'metro'=>'QA: станция тестовая',
            'phone'=>'+7 (812) 000-00-01',
            'phone_href'=>'tel:+78120000001',
            'email'=>'qa-only@museum.invalid',
            'opening_hours'=>'QA: 10:00–17:00',
            'admission_hours'=>'QA: вход до 16:30',
            'closed_day'=>'QA: среда закрыто',
            'sanitary_day'=>'QA: первый понедельник',
        ];
    }
    private function snapshot():array {
        $file=storage_path('framework/testing/visitor-contacts-snapshot.json');
        $manifest=storage_path('framework/testing/visitor-contacts-manifest.json');
        try {
            $this->artisan('museum:export',['--output'=>$file,'--manifest'=>$manifest])
                ->assertSuccessful();
            $this->assertSame(
                hash_file('sha256',$file),
                json_decode(file_get_contents($manifest),true,flags:JSON_THROW_ON_ERROR)['files']['published.json']['sha256']
            );
            return json_decode(file_get_contents($file),true,flags:JSON_THROW_ON_ERROR);
        } finally {@unlink($file);@unlink($manifest);}
    }
    public function test_draft_private_then_complete_approved_card_exports_and_withdraws():void {
        $this->assertArrayNotHasKey('visitor_contacts',$this->snapshot());
        $draft=$this->approved();$draft['status']='draft';
        $draft['address']='СЕКРЕТ: черновик';$draft['email']='private@museum.invalid';
        $record=MuseumVisitorContacts::create($draft);
        $this->assertArrayNotHasKey('visitor_contacts',$this->snapshot());
        $record->update($this->approved());
        $published=$this->snapshot();
        $this->assertSame($this->approved()['address'],$published['visitor_contacts']['address']);
        $this->assertSame($this->approved()['email'],$published['visitor_contacts']['email']);
        $this->assertCount(9,$published['visitor_contacts']);
        $this->assertStringNotContainsString('СЕКРЕТ',json_encode($published,JSON_UNESCAPED_UNICODE));
        $record->update(['address'=>'QA: обновлённый адрес']);
        $this->assertSame('QA: обновлённый адрес',$this->snapshot()['visitor_contacts']['address']);
        $record->update(['status'=>'draft']);
        $this->assertArrayNotHasKey('visitor_contacts',$this->snapshot());
    }
    public function test_complete_approval_and_safe_phone_email_are_mandatory():void {
        foreach([
            ['address'=>''],
            ['email'=>''],
            ['phone_href'=>'https://malicious.example/'],
            ['phone_href'=>'tel:+7<script>'],
            ['email'=>'javascript:evil()'],
            ['scope'=>'secondary'],
            ['status'=>'maybe'],
        ] as $variation) {
            try {
                MuseumVisitorContacts::create(array_merge($this->approved(),$variation));
                $this->fail('Unapproved or malformed CMS data accepted: '.json_encode($variation));
            } catch(ValidationException $e) { $this->assertNotEmpty($e->errors()); }
        }
        $record=MuseumVisitorContacts::create($this->approved());
        $this->assertNotNull($record->id);
        $this->expectException(\Illuminate\Database\UniqueConstraintViolationException::class);
        MuseumVisitorContacts::create($this->approved());
    }
    public function test_editing_contact_card_is_restricted_to_museum_administrator():void {
        $url='/admin/resource/museum-visitor-contacts-resource/visitor-contacts-form-page';
        $this->get($url)->assertRedirect('/admin/login');
        $role=MoonshineUserRole::where('name','Editor')->firstOrFail();
        $editor=MoonshineUser::factory()->create(['moonshine_user_role_id'=>$role->id]);
        $this->actingAs($editor,'moonshine')->get('/admin')->assertOk()
            ->assertDontSee('Контакты и часы работы');
        $this->get($url)->assertForbidden();
        $admin=MoonshineUser::factory()->create();
        $this->actingAs($admin,'moonshine')->get('/admin')->assertOk()
            ->assertSee('Контакты и часы работы');
        $this->get($url)->assertOk()
            ->assertSee('name="address"',false)
            ->assertSee('name="phone_href"',false)
            ->assertSee('name="email"',false)
            ->assertSee('name="status"',false);
    }
}
