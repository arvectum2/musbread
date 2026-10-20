<?php

namespace Tests\Feature;

use App\Models\MuseumEntry;
use App\Models\MuseumSection;
use App\Support\MuseumApprovalRevision;
use Illuminate\Foundation\Testing\RefreshDatabase;
use MoonShine\Laravel\Models\MoonshineUser;
use MoonShine\Laravel\Models\MoonshineUserRole;
use Tests\TestCase;

/** Two browser sessions, one shared SQLite test DB and an actual MoonShine form.
 * Sequential saves are intentional here; separate process concurrency follows.
 */
final class MuseumEntryOptimisticLockTest extends TestCase
{
    use RefreshDatabase;

    private function revisionFromForm(MoonshineUser $editor, MuseumEntry $entry): string
    {
        $html = $this->actingAs($editor, 'moonshine')
            ->get('/admin/resource/museum-entry-resource/museum-entry-form-page/'.$entry->id)
            ->assertOk()->getContent();
        $this->assertMatchesRegularExpression(
            '/name="_museum_revision_sha256"/', $html
        );
        $matches = [];
        $this->assertSame(1, preg_match(
            '/<input[^>]*name="_museum_revision_sha256"[^>]*>/s', $html, $matches
        ));
        $this->assertSame(1, preg_match('/value="([a-f0-9]{64})"/', $matches[0], $value), $matches[0]);
        return $value[1];
    }

    private function update(MuseumEntry $entry, string $revision, string $body, ?string $csrf = null): \Illuminate\Testing\TestResponse
    {
        return $this->patch('/admin/resource/museum-entry-resource/crud/'.$entry->id, [
            '_token' => $csrf,
            '_museum_revision_sha256' => $revision,
            'slug' => $entry->slug, 'type' => $entry->type,
            'title' => $entry->title, 'body' => $body, 'status' => 'draft',
            'museum_section_id' => $entry->museum_section_id,
        ]);
    }

    public function test_two_editors_open_same_page_and_stale_second_save_must_not_overwrite_first(): void
    {
        $section = MuseumSection::create([
            'slug' => 'shared-editor-section', 'title' => 'Общий раздел', 'status' => 'published',
        ]);
        $role = MoonshineUserRole::where('name', 'Editor')->firstOrFail();
        $alice = MoonshineUser::factory()->create(['moonshine_user_role_id' => $role->id]);
        $bob = MoonshineUser::factory()->create(['moonshine_user_role_id' => $role->id]);
        $section->editors()->attach([$alice->id, $bob->id]);
        $entry = MuseumEntry::create([
            'type' => 'news', 'slug' => 'same-news-two-editors',
            'title' => 'Старый материал', 'body' => '<p>Исходный текст</p>',
            'status' => 'draft', 'museum_section_id' => $section->id,
        ]);

        $aliceRevision = $this->revisionFromForm($alice, $entry);
        $bobRevision = $this->revisionFromForm($bob, $entry);
        $this->assertSame($aliceRevision, $bobRevision);
        $this->assertSame(MuseumApprovalRevision::fingerprint($entry->fresh()), $aliceRevision);

        $this->actingAs($alice, 'moonshine');
        $this->update($entry, $aliceRevision, '<p>Правка Алисы</p>')->assertRedirect();
        $this->assertSame('<p>Правка Алисы</p>', $entry->fresh()->body);

        $this->actingAs($bob, 'moonshine');
        $conflict = $this->update($entry, $bobRevision, '<p>Устаревшая правка Боба</p>')
            ->assertStatus(409)
            ->assertSee('Другой редактор изменил материал')
            ->assertSee('Мой несохранённый вариант')
            ->assertSee('Устаревшая правка Боба')
            ->assertSee('Правка Алисы')
            ->assertSee('Сохранить мой черновик')
            ->assertSee('museum-editor-conflict.js');
        $this->assertStringContainsString('no-store', $conflict->headers->get('Cache-Control'));
        $this->assertStringContainsString("script-src 'self'", $conflict->headers->get('Content-Security-Policy'));
        $this->assertSame('<p>Правка Алисы</p>', $entry->fresh()->body);

        $current = $this->revisionFromForm($bob, $entry);
        $this->assertNotSame($bobRevision, $current);
        $this->update($entry, $current, '<p>Правка Боба после обновления</p>')->assertRedirect();
        $this->assertSame('<p>Правка Боба после обновления</p>', $entry->fresh()->body);

        $this->update($entry, '', '<p>Пустой токен</p>')->assertStatus(409);
        $this->update($entry, str_repeat('0', 64), '<p>Поддельный токен</p>')->assertStatus(409);
        $this->assertSame('<p>Правка Боба после обновления</p>', $entry->fresh()->body);
    }

    public function test_stale_html_never_executes_as_markup_or_leaks_private_csrf_data(): void
    {
        $admin = MoonshineUser::factory()->create();
        $entry = MuseumEntry::create([
            'type' => 'news', 'slug' => 'conflict-escaped-data',
            'title' => 'Старая новость',
            'body' => '<p>Текст оригинала</p>',
            'status' => 'draft',
        ]);
        $this->actingAs($admin, 'moonshine');
        $opened = MuseumApprovalRevision::fingerprint($entry->fresh());
        $entry->update(['body' => '<p>Текущая редакция</p>']);
        $malicious = '<script>alert("unexpected")</script> & "test"';
        $result = $this->update($entry, $opened, $malicious)
            ->assertStatus(409)
            ->assertSee('Сохранить мой черновик')
            ->assertSee('Текущая редакция');
        $html = $result->getContent();
        $this->assertStringContainsString('&lt;script&gt;alert', $html);
        $this->assertStringNotContainsString($malicious, $html);
        $this->assertStringContainsString('data-conflict-draft="body"', $html);
        $this->assertStringNotContainsString('_token', $html);
        $this->assertSame('<p>Текущая редакция</p>', $entry->fresh()->body);
    }

    public function test_latest_text_is_not_shown_after_editor_loses_access_to_section(): void
    {
        $own = MuseumSection::create([
            'slug' => 'conflict-allow-section', 'title' => 'Ранее разрешённый раздел',
            'status' => 'published',
        ]);
        $other = MuseumSection::create([
            'slug' => 'conflict-revoked-section', 'title' => 'Закрытый раздел',
            'status' => 'published',
        ]);
        $role = MoonshineUserRole::where('name', 'Editor')->firstOrFail();
        $editor = MoonshineUser::factory()->create(['moonshine_user_role_id' => $role->id]);
        $own->editors()->attach($editor->id);
        $entry = MuseumEntry::create([
            'type' => 'news', 'slug' => 'conflict-revoked-article',
            'title' => 'До перевода', 'body' => '<p>Исходный</p>',
            'museum_section_id' => $own->id, 'status' => 'draft',
        ]);
        $revision = $this->revisionFromForm($editor, $entry);
        // The administrator moves this item to another editor's section.
        $this->actingAs(MoonshineUser::factory()->create(), 'moonshine');
        $entry->update(['museum_section_id' => $other->id,
            'body' => '<p>Закрытый текст другого раздела</p>']);
        $this->actingAs($editor, 'moonshine');
        $result = $this->update($entry, $revision, '<p>Несданная версия');
        $this->assertContains($result->status(), [302, 403, 404],
            'A revoked editor may never receive a 409 diff showing a now-private entry');
        $result->assertDontSee('Закрытый текст другого раздела');
        $this->assertSame('<p>Закрытый текст другого раздела</p>', $entry->fresh()->body);
    }

    public function test_conflict_page_works_with_moonshine_production_error_handling(): void
    {
        $admin = MoonshineUser::factory()->create();
        $entry = MuseumEntry::create([
            'type' => 'news', 'slug' => 'conflict-production-flow',
            'title' => 'Старая новость',
            'body' => '<p>Исходная редакция</p>',
            'status' => 'draft',
        ]);
        $this->actingAs($admin, 'moonshine');
        $oldRevision = MuseumApprovalRevision::fingerprint($entry->fresh());
        $entry->update(['body' => '<p>Актуальный вариант</p>']);
        $previous = app()->environment();
        app()->instance('env', 'production');
        try {
            $this->withSession(['_token' => 'conflict-form-csrf-token']);
            $this->update($entry, $oldRevision, '<p>Текст, который нужно сохранить</p>', 'conflict-form-csrf-token')
                ->assertStatus(409)
                ->assertSee('Текст, который нужно сохранить')
                ->assertSee('Актуальный вариант');
        } finally {
            app()->instance('env', $previous);
        }
        $this->assertSame('<p>Актуальный вариант</p>', $entry->fresh()->body);
    }

}
