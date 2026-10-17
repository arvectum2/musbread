<?php

declare(strict_types=1);

namespace Tests\Feature;

use App\Models\MuseumAuditRecord;
use App\Models\MuseumPublicationRun;
use App\Models\MuseumEntry;
use App\Models\MuseumEvent;
use App\Models\MuseumSection;
use Illuminate\Support\Carbon;
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
    public function test_date_range_is_inclusive_and_daily_rollup_respects_employee_filter(): void
    {
        $admin = MoonshineUser::factory()->create();
        $editorRole = MoonshineUserRole::query()->where('name', 'Editor')->firstOrFail();
        $editor = MoonshineUser::factory()->create(['moonshine_user_role_id' => $editorRole->id]);
        $this->travelTo(Carbon::parse('2026-10-17 12:00:00', 'UTC'));

        $this->actingAs($admin, 'moonshine');
        foreach ([
            ['2026-10-15 09:00:00', $admin->id, 'created'],
            ['2026-10-16 09:00:00', $editor->id, 'updated'],
            ['2026-10-16 10:00:00', $admin->id, 'deleted'],
            ['2026-10-17 23:59:59', $editor->id, 'updated'],
        ] as [$time, $actor, $action]) {
            // Insert timestamps explicitly: the tested SQL must honor end of day.
            \Illuminate\Support\Facades\DB::table('museum_audit_records')->insert([
                'subject_type'=>'MuseumEntry', 'subject_id'=>71,
                'actor_id'=>$actor, 'action'=>$action, 'changed_fields'=>'[]',
                'created_at'=>$time,
            ]);
        }

        $url = route('museum.activity.stats', [
            'from'=>'2026-10-16', 'to'=>'2026-10-17', 'actor_id'=>$editor->id,
        ]);
        $response = $this->get($url);
        $response->assertOk()
            ->assertSee('16.10.2026 — 17.10.2026')
            ->assertSee('По дату (включительно)')
            ->assertSee('Динамика по дням')
            ->assertSee('2026-10-16')->assertSee('2026-10-17')
            ->assertDontSee('2026-10-15')
            ->assertSee('Изменение')
            ->assertDontSee('Удаление');
        $this->assertSame(2, substr_count($response->getContent(), '2026-10-16</td>') +
            substr_count($response->getContent(), '2026-10-17</td>'));

        $this->get(route('museum.activity.stats', ['from'=>'2026-10-17','to'=>'2026-10-16']))
            ->assertStatus(422);
        $this->get(route('museum.activity.stats', ['to'=>'1900-01-01']))
            ->assertStatus(422);
        $this->get(route('museum.activity.stats', ['to'=>'2099-01-01']))
            ->assertStatus(422);
        $this->get(route('museum.activity.stats', ['to'=>'2026-10-17','actor_id'=>'1 OR 1=1']))
            ->assertSessionHasErrors('actor_id');
    }

    public function test_publication_outcomes_and_drafts_are_global_and_private(): void
    {
        $admin = MoonshineUser::factory()->create();
        $role = MoonshineUserRole::query()->where('name', 'Editor')->firstOrFail();
        $editor = MoonshineUser::factory()->create(['moonshine_user_role_id'=>$role->id]);
        $this->actingAs($admin, 'moonshine');

        MuseumPublicationRun::create(['status'=>'failed','attempts'=>2, 'error_type'=>'RuntimeException']);
        MuseumPublicationRun::create(['status'=>'succeeded','attempts'=>1,
            'snapshot_sha256'=>str_repeat('f',64)]);
        MuseumPublicationRun::create(['status'=>'queued','attempts'=>0]);
        MuseumSection::create(['slug'=>'pending-section','title'=>'Частный раздел','status'=>'draft']);
        MuseumEntry::create(['slug'=>'draft-material','title'=>'Частный материал',
            'type'=>'page','status'=>'draft','body'=>'Скрытый текст']);
        MuseumEvent::create(['slug'=>'draft-schedule', 'title'=>'Частный анонс',
            'category'=>'Выставка', 'starts_at'=>'2026-11-10',
            'body'=>'Скрытая программа','excerpt'=>'Черновик','status'=>'draft']);

        $response = $this->get(route('museum.activity.stats', ['actor_id'=>$editor->id]))
            ->assertOk()->assertSee('Публикации статического сайта')
            ->assertSee('Динамика по дням')
            ->assertSee('Успешно подготовлен')->assertSee('Ошибка')->assertSee('В очереди')
            ->assertSee('Черновики материалов')->assertSee('Черновики событий')
            ->assertSee('Черновики разделов')
            ->assertDontSee('Скрытый текст')->assertDontSee('Скрытая программа')
            ->assertDontSee(str_repeat('f', 64))->assertDontSee('RuntimeException')
            ->assertHeader('X-Robots-Tag', 'noindex, nofollow, noarchive');
        $this->assertSame(3, substr_count($response->getContent(), '<td>#'));
        $this->actingAs($editor,'moonshine')->get(route('museum.activity.stats'))->assertForbidden();
    }


    public function test_publication_readiness_never_counts_hidden_section_as_public(): void
    {
        $this->travelTo(Carbon::parse('2026-10-17 12:00:00', 'UTC'));
        $this->actingAs(MoonshineUser::factory()->create(), 'moonshine');

        $visibleSection = MuseumSection::create([
            'slug'=>'visible-root','title'=>'Видимый раздел','status'=>'published',
        ]);
        $hiddenParent = MuseumSection::create([
            'slug'=>'unapproved-parent','title'=>'Скрытый родитель','status'=>'draft',
        ]);
        $blockedChild = MuseumSection::create([
            'slug'=>'blocked-child','title'=>'Опубликованный дочерний','status'=>'published',
            'parent_id'=>$hiddenParent->id,
        ]);
        foreach ([
            ['visible-content', $visibleSection->id, null],
            ['blocked-content', $blockedChild->id, null],
            ['expired-content', $visibleSection->id, '2026-10-17 11:59:59'],
        ] as [$slug,$sectionId,$expiry]) {
            MuseumEntry::create([
                'type'=>'news','title'=>$slug,'slug'=>$slug,'body'=>'Статья',
                'status'=>'published','published_at'=>'2026-10-16 09:00:00',
                'unpublish_at'=>$expiry, 'museum_section_id'=>$sectionId,
            ]);
        }
        foreach ([
            ['visible-event',$visibleSection->id,null],
            ['blocked-event',$blockedChild->id,null],
            ['expired-event',$visibleSection->id,'2026-10-17 11:59:59'],
        ] as [$slug,$sectionId,$expiry]) {
            MuseumEvent::create([
                'title'=>$slug,'slug'=>$slug,'category'=>'Выставка',
                'starts_at'=>'2026-11-12','excerpt'=>'Анонс','body'=>'Программа',
                'status'=>'published','published_at'=>'2026-10-16 09:00:00',
                'unpublish_at'=>$expiry,'museum_section_id'=>$sectionId,
            ]);
        }

        $html = $this->get(route('museum.activity.stats'))->assertOk()->getContent();
        foreach ([
            'Материалы готовы к следующей выгрузке'=>1,
            'Материалы ожидают даты публикации'=>0,
            'Материалы сняты по сроку'=>1,
            'События готовы к следующей выгрузке'=>1,
            'События ожидают даты публикации'=>0,
            'События сняты по сроку'=>1,
        ] as $label=>$expected) {
            $pattern='/'.preg_quote($label,'/').'<br><strong>(\d+)<\/strong>/u';
            $this->assertSame(1, preg_match($pattern, $html, $matched), $label);
            $this->assertSame($expected,(int)$matched[1], $label);
        }
        // Audit report must not silently change the status of hidden items.
        $this->assertDatabaseHas('museum_entries', ['slug'=>'blocked-content','status'=>'published']);
        $this->assertDatabaseHas('museum_events', ['slug'=>'blocked-event','status'=>'published']);
    }

}
