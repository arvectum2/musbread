<?php

namespace Tests\Feature;

use App\Models\MuseumAuditRecord;
use App\Models\MuseumEntry;
use Illuminate\Foundation\Testing\RefreshDatabase;
use MoonShine\Laravel\Models\MoonshineUser;
use Tests\TestCase;

class MuseumAuditTest extends TestCase
{
    use RefreshDatabase;

    private function content(): array
    {
        return [
            'type' => 'news',
            'slug' => 'audited-story',
            'title' => 'События музея',
            'body' => 'Секретный тестовый текст, не дублировать в аудите',
            'status' => 'draft',
        ];
    }

    public function test_create_update_delete_append_an_audit_trail_without_content_values(): void
    {
        $admin = MoonshineUser::factory()->create();
        $this->actingAs($admin, 'moonshine');

        $entry = MuseumEntry::create($this->content());
        $entry->update(['body' => 'Новый текст, не дублировать', 'status' => 'published']);
        $id = $entry->id;
        $entry->delete();

        $records = MuseumAuditRecord::query()->orderBy('id')->get();
        $this->assertSame(['created', 'updated', 'deleted'], $records->pluck('action')->all());
        $this->assertEqualsCanonicalizing(['body', 'status', 'published_at'], $records[1]->changed_fields);
        $this->assertSame($admin->id, $records[0]->actor_id);
        $this->assertSame($id, $records[2]->subject_id);
        $this->assertStringNotContainsString(
            'Новый текст',
            $records->toJson(JSON_UNESCAPED_UNICODE)
        );
        $this->assertStringNotContainsString(
            'Секретный',
            $records->toJson(JSON_UNESCAPED_UNICODE)
        );
    }

    public function test_audit_ui_is_read_only_and_superuser_only(): void
    {
        $editorRole = \MoonShine\Laravel\Models\MoonshineUserRole::where('name', 'Editor')->firstOrFail();
        $editor = MoonshineUser::factory()->create(['moonshine_user_role_id' => $editorRole->id]);
        $this->actingAs($editor, 'moonshine');
        $this->get('/admin/resource/museum-audit-record-resource/museum-audit-record-index-page')
            ->assertForbidden();
        $this->post('/admin/resource/museum-audit-record-resource/crud', [
            'subject_type' => 'Spoof', 'subject_id' => 999, 'action' => 'created',
        ])->assertForbidden();

        $admin = MoonshineUser::factory()->create();
        $this->actingAs($admin, 'moonshine');
        $this->get('/admin/resource/museum-audit-record-resource/museum-audit-record-index-page')
            ->assertOk();
        $this->post('/admin/resource/museum-audit-record-resource/crud', [
            'subject_type' => 'Spoof', 'subject_id' => 999, 'action' => 'created',
        ])->assertForbidden();
        $this->assertSame(0, MuseumAuditRecord::count());
    }

    public function test_public_export_never_contains_audit_records_or_editor_id(): void
    {
        $admin = MoonshineUser::factory()->create();
        $this->actingAs($admin, 'moonshine');
        MuseumEntry::create($this->content());

        $out = storage_path('framework/testing/audit-private.json');
        $manifest = storage_path('framework/testing/audit-private-manifest.json');
        try {
            $this->artisan('museum:export', ['--output' => $out, '--manifest' => $manifest])->assertSuccessful();
            $raw = file_get_contents($out);
            $this->assertStringNotContainsString('actor_id', $raw);
            $this->assertStringNotContainsString('changed_fields', $raw);
            $this->assertStringNotContainsString('audited-story', $raw);
        } finally {
            @unlink($out);
            @unlink($manifest);
        }
    }
}
