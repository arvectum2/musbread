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

    private function update(MuseumEntry $entry, string $revision, string $body): \Illuminate\Testing\TestResponse
    {
        return $this->patch('/admin/resource/museum-entry-resource/crud/'.$entry->id, [
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
        $this->update($entry, $bobRevision, '<p>Устаревшая правка Боба</p>')->assertStatus(409);
        $this->assertSame('<p>Правка Алисы</p>', $entry->fresh()->body);

        $current = $this->revisionFromForm($bob, $entry);
        $this->assertNotSame($bobRevision, $current);
        $this->update($entry, $current, '<p>Правка Боба после обновления</p>')->assertRedirect();
        $this->assertSame('<p>Правка Боба после обновления</p>', $entry->fresh()->body);

        $this->update($entry, '', '<p>Пустой токен</p>')->assertStatus(409);
        $this->update($entry, str_repeat('0', 64), '<p>Поддельный токен</p>')->assertStatus(409);
        $this->assertSame('<p>Правка Боба после обновления</p>', $entry->fresh()->body);
    }
}
