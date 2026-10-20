<?php

namespace Tests\Feature;

use App\Models\MuseumContentApproval;
use App\Models\MuseumEntry;
use App\Models\MuseumEvent;
use App\Models\MuseumPublicationRun;
use App\Models\MuseumSection;
use App\Support\MuseumApprovalRevision;
use Illuminate\Foundation\Testing\RefreshDatabase;
use MoonShine\Laravel\Models\MoonshineUser;
use MoonShine\Laravel\Models\MoonshineUserRole;
use Tests\TestCase;

final class MuseumPublicationJourneyStatusTest extends TestCase
{
    use RefreshDatabase;

    private function news(string $slug = 'publication-step'): MuseumEntry
    {
        return MuseumEntry::create([
            'type' => 'news', 'slug' => $slug,
            'title' => 'Синтетическая новость',
            'body' => '<p>Тестовые сведения о хлебе</p>',
            'status' => 'published',
        ]);
    }

    private function approval(MuseumEntry $entry, string $dispatch, ?MuseumPublicationRun $run = null): MuseumContentApproval
    {
        return MuseumContentApproval::create([
            'museum_entry_id' => $entry->id,
            'actor_id' => 1,
            'revision_sha256' => MuseumApprovalRevision::fingerprint($entry->fresh()),
            'approved_at' => now('UTC'),
            'dispatch_status' => $dispatch,
            'publication_run_id' => $run?->id,
        ]);
    }

    public function test_journal_distinguishes_saved_revision_from_approval_queue_and_successful_private_export(): void
    {
        $this->actingAs(MoonshineUser::factory()->create(), 'moonshine');
        $entry = $this->news();
        $run = MuseumPublicationRun::create([
            'status' => 'queued', 'attempts' => 0,
        ]);
        $this->approval($entry, 'queued', $run);

        $journal = route('museum.content.approval-journal');
        $this->get($journal)->assertOk()
            ->assertSee('SHA-256 совпадает с текущей редакцией')
            ->assertSee('Запрос на закрытую выгрузку зарегистрирован')
            ->assertSee('Ожидает фонового обработчика')
            ->assertSee('не является')
            ->assertDontSee('Приватный пакет подготовлен')
            ->assertHeader('Cache-Control', 'max-age=0, no-store, private');

        $run->update(['status' => 'running', 'attempts' => 1, 'started_at' => now()]);
        $this->get($journal)->assertOk()
            ->assertSee('Подготовка приватного пакета выполняется');

        $run->update(['status' => 'failed', 'error_type' => 'RuntimeException', 'finished_at' => now()]);
        $this->get($journal)->assertOk()
            ->assertSee('Ошибка подготовки приватного пакета')
            ->assertSee('Приватный пакет не подтверждён как подготовленный')
            ->assertSee('RuntimeException');

        $run->update([
            'status' => 'succeeded', 'error_type' => null,
            'snapshot_sha256' => str_repeat('b', 64),
        ]);
        $this->get($journal)->assertOk()
            ->assertSee('Приватный пакет подготовлен')
            ->assertSee(str_repeat('b', 64))
            ->assertSee('Он сам по себе не подтверждает')
            ->assertDontSee('Приватный пакет не подтверждён как подготовленный');

        // A subsequent revision invalidates the historic approval but must
        // not rewrite the original approval timestamp or the prior run.
        $entry->update(['body' => '<p>Текст обновлён позднее</p>']);
        $this->get($journal)->assertOk()
            ->assertSee('Редакция изменилась после одобрения; требуется новое решение')
            ->assertSee('Приватный пакет подготовлен')
            ->assertDontSee('Текст обновлён позднее');
        $this->assertDatabaseCount('museum_content_approvals', 1);
        $this->assertSame('succeeded', $run->fresh()->status);
    }

    public function test_missing_subject_failed_dispatch_and_missing_run_are_not_mistaken_for_publication(): void
    {
        $this->actingAs(MoonshineUser::factory()->create(), 'moonshine');
        $entry = $this->news('missing-step');
        $this->approval($entry, 'failed');
        $entry->delete();

        $this->get(route('museum.content.approval-journal'))->assertOk()
            ->assertSee('Объект отсутствует в текущей CMS')
            ->assertSee('постановка в очередь завершилась ошибкой')
            ->assertSee('Запуск ещё не привязан')
            ->assertDontSee('Приватный пакет подготовлен');

        $replacement = $this->news('missing-linked-run');
        $missingRun = MuseumPublicationRun::create(['status' => 'queued']);
        $approval = $this->approval($replacement, 'queued', $missingRun);
        $missingRun->delete();
        $this->get(route('museum.content.approval-journal'))->assertOk()
            ->assertSee('Связанный запуск отсутствует в базе')
            ->assertDontSee('Ошибка подготовки приватного пакета');
        $this->assertSame($approval->id, MuseumContentApproval::query()->latest('id')->value('id'));
    }

    public function test_event_and_section_approvals_are_verified_against_current_saved_versions(): void
    {
        $this->actingAs(MoonshineUser::factory()->create(), 'moonshine');
        $event = MuseumEvent::create([
            'slug' => 'synthetic-tour',
            'title' => 'Синтетическая экскурсия',
            'category' => 'Экскурсия',
            'excerpt' => 'Тестовая программа',
            'body' => '<p>Событие для проверки статусов</p>',
            'starts_at' => now()->addDay(),
            'status' => 'draft',
        ]);
        $section = MuseumSection::create([
            'slug' => 'synthetic-section', 'title' => 'Тестовый раздел',
            'status' => 'published',
        ]);
        foreach ([
            ['museum_event_id' => $event->id, 'revision_sha256' => MuseumApprovalRevision::forSubject($event->fresh())],
            ['museum_section_id' => $section->id, 'revision_sha256' => MuseumApprovalRevision::forSubject($section->fresh())],
        ] as $attrs) {
            MuseumContentApproval::create($attrs + [
                'actor_id' => 1, 'approved_at' => now('UTC'), 'dispatch_status' => 'pending',
            ]);
        }
        $this->get(route('museum.content.approval-journal'))->assertOk()
            ->assertSee('Событие #'.$event->id)
            ->assertSee('Раздел #'.$section->id)
            ->assertSee('SHA-256 совпадает с текущей редакцией')
            ->assertSee('Одобрено; запрос выгрузки ещё не подтверждён');

        $section->update(['title' => 'Поменяли структуру раздела']);
        $this->get(route('museum.content.approval-journal'))->assertOk()
            ->assertSee('Редакция изменилась после одобрения; требуется новое решение');
    }

    public function test_preflight_shows_only_last_private_run_with_a_direct_audit_followup(): void
    {
        $this->actingAs(MoonshineUser::factory()->create(), 'moonshine');
        $this->get(route('museum.content.preflight'))->assertOk()
            ->assertSee('Задания закрытой выгрузки ещё не создавались')
            ->assertSee('Посмотреть одобрения, актуальность редакций и результаты заданий');

        $old = MuseumPublicationRun::create(['status' => 'succeeded',
            'snapshot_sha256' => str_repeat('a', 64)]);
        $last = MuseumPublicationRun::create(['status' => 'failed',
            'attempts' => 1, 'error_type' => 'RuntimeException']);
        $this->get(route('museum.content.preflight'))->assertOk()
            ->assertSee('Запуск #'.$last->id)
            ->assertSee('Ошибка подготовки приватного пакета')
            ->assertSee('Пакет не подтверждён как подготовленный')
            ->assertDontSee('Запуск #'.$old->id);
        $last->update(['status' => 'succeeded',
            'snapshot_sha256' => str_repeat('b', 64)]);
        $this->get(route('museum.content.preflight'))->assertOk()
            ->assertSee('Приватный пакет подготовлен')
            ->assertSee('не публичный сайт');
    }

    public function test_journal_is_admin_only_and_exposes_no_status_to_editor_or_guest(): void
    {
        $entry = $this->news();
        $this->approval($entry, 'pending');
        $url = route('museum.content.approval-journal');
        $this->get($url)->assertRedirect('/admin/login');
        $role = MoonshineUserRole::where('name', 'Editor')->firstOrFail();
        $this->actingAs(
            MoonshineUser::factory()->create(['moonshine_user_role_id' => $role->id]), 'moonshine'
        );
        $this->get($url)->assertForbidden()->assertDontSee($entry->title);
        $this->get(route('museum.content.preflight'))->assertOk()
            ->assertDontSee('Ход закрытых выгрузок');
        $this->actingAs(MoonshineUser::factory()->create(), 'moonshine');
        $this->get('/admin/resource/museum-entry-resource/museum-entry-index-page')->assertOk()
            ->assertSee('Ход закрытых выгрузок');
    }
}
