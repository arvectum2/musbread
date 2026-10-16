<?php

declare(strict_types=1);

namespace Tests\Feature;

use App\Models\MuseumAuditRecord;
use Illuminate\Auth\Events\Login;
use Illuminate\Auth\Events\Logout;
use Illuminate\Foundation\Testing\RefreshDatabase;
use MoonShine\Laravel\Models\MoonshineUser;
use MoonShine\Laravel\Models\MoonshineUserRole;
use Tests\TestCase;

final class MuseumActivityStatisticsTest extends TestCase
{
    use RefreshDatabase;

    public function test_login_logout_and_aggregates_are_superuser_only(): void
    {
        $admin=MoonshineUser::factory()->create();
        $role=MoonshineUserRole::query()->where('name','Editor')->firstOrFail();
        $editor=MoonshineUser::factory()->create(['moonshine_user_role_id'=>$role->id]);
        $this->get(route('museum.activity.stats'))->assertRedirect('/admin/login');
        $this->actingAs($editor,'moonshine')->get(route('museum.activity.stats'))->assertForbidden();
        event(new Login('web', $admin, false));
        $this->assertDatabaseCount('museum_audit_records',0);
        event(new Login('moonshine', $admin, false));
        event(new Logout('moonshine', $admin));
        MuseumAuditRecord::query()->create([
            'subject_type'=>'MuseumEntry','subject_id'=>1,'action'=>'updated',
            'actor_id'=>$admin->id,'changed_fields'=>['title'],
        ]);
        MuseumAuditRecord::query()->create([
            'subject_type'=>'MuseumEntry','subject_id'=>2,'action'=>'deleted',
            'actor_id'=>$editor->id,'changed_fields'=>[],
        ]);
        $this->assertDatabaseCount('museum_audit_records',4);
        $response=$this->actingAs($admin,'moonshine')->get(route('museum.activity.stats'));
        $response->assertOk()->assertSee('Статистика действий сотрудников')
            ->assertSee('Вход в CMS')->assertSee('Выход из CMS')->assertSee('Изменение')
            ->assertSee('MoonshineUser')->assertSee('Сотрудников');
        $this->assertStringContainsString('no-store', $response->headers->get('Cache-Control'));
        $response->assertHeader('X-Robots-Tag','noindex, nofollow, noarchive');
        $response->assertDontSee('title</td>',false);
        $this->get(route('museum.activity.stats',['actor_id'=>$editor->id]))->assertOk()
            ->assertSee('Записей')->assertDontSee('Вход в CMS');
        $this->get(route('museum.activity.stats',['from'=>'1900-01-01']))->assertStatus(422);
        $this->get(route('museum.activity.stats',['actor_id'=>'nope']))->assertSessionHasErrors('actor_id');
    }

    public function test_html_is_escaped_and_no_private_audit_records_enter_public_export(): void
    {
        $admin=MoonshineUser::factory()->create();
        $this->actingAs($admin,'moonshine');
        MuseumAuditRecord::query()->create([
            'subject_type'=>'<script>alert(1)</script>','subject_id'=>4,'action'=>'updated',
            'actor_id'=>$admin->id,'changed_fields'=>['private_filename'],
        ]);
        $this->get(route('museum.activity.stats'))->assertOk()
            ->assertDontSee('<script>alert(1)</script>',false)
            ->assertSee('&lt;script&gt;alert(1)&lt;/script&gt;',false)
            ->assertDontSee('private_filename');
        $destination=storage_path('framework/testing/activity-export.json');
        $manifest=storage_path('framework/testing/activity-export-manifest.json');
        try {
            $this->artisan('museum:export',['--output'=>$destination,'--manifest'=>$manifest])->assertSuccessful();
            $contents=file_get_contents($destination);
            $this->assertStringNotContainsString('private_filename',$contents);
            $this->assertStringNotContainsString('actor_id',$contents);
        } finally { @unlink($destination); @unlink($manifest); }
    }
}
