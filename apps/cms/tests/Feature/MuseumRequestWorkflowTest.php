<?php

namespace Tests\Feature;

use App\Models\MuseumAuditRecord;
use Database\Seeders\ReferenceMuseumSectionsSeeder;
use Database\Seeders\DemoMuseumRequestsSeeder;
use App\Models\MuseumRequest;
use App\Models\MuseumRequestTransition;
use App\Models\MuseumSection;
use Illuminate\Auth\Access\AuthorizationException;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Validation\ValidationException;
use MoonShine\Laravel\Models\MoonshineUser;
use MoonShine\Laravel\Models\MoonshineUserRole;
use Tests\TestCase;

class MuseumRequestWorkflowTest extends TestCase
{
    use RefreshDatabase;

    private function admin(): MoonshineUser
    {
        return MoonshineUser::factory()->create();
    }

    private function editor(): MoonshineUser
    {
        $role = MoonshineUserRole::where('name', 'Editor')->firstOrFail();
        return MoonshineUser::factory()->create(['moonshine_user_role_id' => $role->id]);
    }

    private function section(string $slug): MuseumSection
    {
        return MuseumSection::create([
            'slug' => $slug, 'title' => 'Раздел '.$slug, 'status' => 'published',
        ]);
    }

    private function feedback(array $overrides = []): MuseumRequest
    {
        return MuseumRequest::create(array_merge([
            'type' => 'feedback', 'topic' => 'general', 'status' => 'new',
        ], $overrides));
    }

    public function test_admin_creates_internal_demo_case_through_moonshine_but_no_personal_data(): void
    {
        $this->actingAs($this->admin(), 'moonshine')
            ->post('/admin/resource/museum-request-resource/crud', [
                'type' => 'feedback', 'topic' => 'accessibility', 'status' => 'new',
                'name' => 'НЕ СОХРАНЯТЬ ЭТО ПОЛЕ',
                'email' => 'not-recorded@example.invalid',
            ])->assertRedirect();

        $this->assertSame(1, MuseumRequest::count());
        $case = MuseumRequest::firstOrFail();
        $this->assertMatchesRegularExpression('/^DEMO-[A-Z0-9]{26}$/', $case->reference);
        $this->assertSame('internal_demo', $case->origin);
        $this->assertSame('new', $case->status);
        $this->assertDatabaseCount('museum_request_transitions', 1);
        $this->assertFalse(\Schema::hasColumn('museum_requests', 'email'));
        $this->assertFalse(\Schema::hasColumn('museum_requests', 'name'));
        $this->assertFalse(\Schema::hasColumn('museum_requests', 'message'));
        $this->assertStringNotContainsString('not-recorded@example.invalid', $case->toJson());
    }

    public function test_admin_can_open_the_form_and_assign_a_permitted_editor(): void
    {
        $section = $this->section('excursions-test');
        $editor = $this->editor();
        $section->editors()->attach($editor->id);
        $this->actingAs($this->admin(), 'moonshine')
            ->get('/admin/resource/museum-request-resource/museum-request-form-page')
            ->assertOk()
            ->assertSee('Тема');

        $this->post('/admin/resource/museum-request-resource/crud', [
            'type' => 'feedback', 'topic' => 'visit', 'status' => 'new',
            'museum_section_id' => $section->id, 'assigned_to_id' => $editor->id,
        ])->assertRedirect();
        $this->assertDatabaseHas('museum_requests', [
            'assigned_to_id' => $editor->id, 'museum_section_id' => $section->id,
        ]);
    }

    public function test_invalid_http_status_transition_does_not_modify_case(): void
    {
        $case = $this->feedback();
        $this->actingAs($this->admin(), 'moonshine')
            ->patch('/admin/resource/museum-request-resource/crud/'.$case->id, [
                'type' => 'feedback', 'topic' => 'general',
                'status' => 'resolved',
            ])->assertRedirect();
        $this->assertSame('new', $case->fresh()->status);
        $this->assertSame(['new'], $case->transitions()->pluck('to_status')->all());
    }

    public function test_synthetic_opt_in_seeder_populates_two_cases_and_does_not_duplicate(): void
    {
        $this->seed(ReferenceMuseumSectionsSeeder::class);
        $this->seed(DemoMuseumRequestsSeeder::class);
        $this->assertSame(2, MuseumRequest::count());
        $this->assertSame(1, MuseumRequest::where('type', 'excursion')->count());
        $this->seed(DemoMuseumRequestsSeeder::class);
        $this->assertSame(2, MuseumRequest::count());
        $this->assertSame(2, MuseumRequestTransition::count());
    }

    public function test_demo_excursion_validates_date_and_group_size_and_notifies_nobody(): void
    {
        $this->actingAs($this->admin(), 'moonshine')
            ->post('/admin/resource/museum-request-resource/crud', [
                'type' => 'excursion', 'topic' => 'excursion_group',
                'preferred_date' => '2026-12-02', 'group_size' => 12, 'status' => 'new',
            ])->assertRedirect();
        $case = MuseumRequest::firstOrFail();
        $this->assertSame('excursion', $case->type);
        $this->assertSame('2026-12-02', $case->preferred_date->toDateString());
        $this->assertSame(12, $case->group_size);
    }

    public function test_excursion_without_group_size_is_rejected_and_feedback_cannot_have_group(): void
    {
        $this->expectException(ValidationException::class);
        $this->feedback([
            'type' => 'excursion', 'topic' => 'excursion_group',
            'preferred_date' => '2026-12-02',
        ]);
    }

    public function test_feedback_never_has_excursion_date_or_group_count(): void
    {
        $this->expectException(ValidationException::class);
        $this->feedback(['group_size' => 20]);
    }

    public function test_status_transitions_are_ordered_and_audited_without_customer_content(): void
    {
        $admin = $this->admin();
        $this->actingAs($admin, 'moonshine');
        $case = $this->feedback();
        $case->update(['status' => 'triaged']);
        $case->update(['status' => 'in_progress']);
        $case->update(['status' => 'resolved']);
        $this->assertNotNull($case->fresh()->resolved_at);
        $case->update(['status' => 'triaged']);
        $this->assertNull($case->fresh()->resolved_at);
        $this->assertSame(['new', 'triaged', 'in_progress', 'resolved', 'triaged'],
            $case->transitions()->orderBy('id')->pluck('to_status')->all());
        $this->assertSame([null, 'new', 'triaged', 'in_progress', 'resolved'],
            $case->transitions()->orderBy('id')->pluck('from_status')->all());
        $this->assertEqualsCanonicalizing([$admin->id],
            $case->transitions()->pluck('actor_id')->unique()->all());
        $records = MuseumAuditRecord::where('subject_type', 'MuseumRequest')->get();
        $this->assertSame(['created', 'updated', 'updated', 'updated', 'updated'],
            $records->pluck('action')->all());
        $this->assertStringNotContainsString('DEMO-', $records->toJson());
    }

    public function test_invalid_status_jump_from_new_to_resolved_is_rejected(): void
    {
        $case = $this->feedback();
        $this->expectException(ValidationException::class);
        $case->update(['status' => 'resolved']);
    }

    public function test_admin_can_assign_case_only_to_editor_authorized_for_section(): void
    {
        $section = $this->section('visitors');
        $editor = $this->editor();
        $case = $this->feedback(['museum_section_id' => $section->id]);
        try {
            $case->update(['assigned_to_id' => $editor->id]);
            $this->fail('The editor lacks permission for this section.');
        } catch (ValidationException $exception) {
            $this->assertArrayHasKey('assigned_to_id', $exception->errors());
        }
        $section->editors()->attach($editor->id);
        $case->update(['assigned_to_id' => $editor->id]);
        $this->assertSame($editor->id, $case->fresh()->assigned_to_id);
    }

    public function test_editor_can_advance_assigned_case_but_cannot_reassign_or_access_other_cases(): void
    {
        $section = $this->section('visitor-info');
        $editor = $this->editor();
        $otherEditor = $this->editor();
        $section->editors()->attach([$editor->id, $otherEditor->id]);
        $ownCase = $this->feedback([
            'museum_section_id' => $section->id, 'assigned_to_id' => $editor->id,
        ]);
        $otherCase = $this->feedback([
            'museum_section_id' => $section->id, 'assigned_to_id' => $otherEditor->id,
        ]);
        $this->actingAs($editor, 'moonshine');

        $this->get('/admin/resource/museum-request-resource/museum-request-index-page')
            ->assertOk()->assertDontSee($otherCase->reference);
        $this->assertEqualsCanonicalizing([$ownCase->id],
            MuseumRequest::query()->visibleTo($editor)->pluck('id')->all());
        $this->get('/admin/resource/museum-request-resource/museum-request-form-page/'.$otherCase->id)
            ->assertNotFound();
        $this->patch('/admin/resource/museum-request-resource/crud/'.$ownCase->id, [
            'status' => 'triaged',
        ])->assertRedirect();
        $this->assertSame('triaged', $ownCase->fresh()->status);

        // Assigning another person via forged POST/PATCH is not a permitted edit.
        $this->patch('/admin/resource/museum-request-resource/crud/'.$ownCase->id, [
            'status' => 'in_progress', 'assigned_to_id' => $otherEditor->id,
            'topic' => 'event',
        ])->assertRedirect();
        $this->assertSame($editor->id, $ownCase->fresh()->assigned_to_id);
        $this->assertSame('general', $ownCase->fresh()->topic);
        $this->assertSame('in_progress', $ownCase->fresh()->status);

        $this->patch('/admin/resource/museum-request-resource/crud/'.$otherCase->id, [
            'status' => 'triaged',
        ])->assertForbidden();
        $this->assertSame('new', $otherCase->fresh()->status);
    }

    public function test_editor_cannot_create_delete_or_read_all_cases(): void
    {
        $editor = $this->editor();
        $case = $this->feedback();
        $this->actingAs($editor, 'moonshine');
        $this->post('/admin/resource/museum-request-resource/crud', [
            'type' => 'feedback', 'topic' => 'general', 'status' => 'new',
        ])->assertForbidden();
        $this->delete('/admin/resource/museum-request-resource/crud/'.$case->id)
            ->assertForbidden();
        $this->assertDatabaseCount('museum_requests', 1);
        $this->get('/admin/resource/museum-request-transition-resource/museum-request-transition-index-page')
            ->assertForbidden();
    }

    public function test_admin_cannot_delete_cases_or_rewrite_transition_history_from_ui(): void
    {
        $case = $this->feedback();
        $this->actingAs($this->admin(), 'moonshine');
        $this->delete('/admin/resource/museum-request-resource/crud/'.$case->id)->assertForbidden();
        $this->post('/admin/resource/museum-request-transition-resource/crud', [
            'museum_request_id' => $case->id, 'to_status' => 'resolved',
        ])->assertForbidden();
        $this->get('/admin/resource/museum-request-transition-resource/museum-request-transition-index-page')
            ->assertOk();
        $this->assertDatabaseCount('museum_request_transitions', 1);
    }

    public function test_model_rejects_unapproved_mutations_even_without_http_resource(): void
    {
        $case = $this->feedback();
        $this->expectException(ValidationException::class);
        $case->origin = 'public_web';
        $case->save();
    }

    public function test_internal_demo_creates_are_fail_closed_in_production(): void
    {
        $previousEnvironment = app()->environment();
        app()->instance('env', 'production');
        try {
            $this->expectException(AuthorizationException::class);
            $this->feedback();
        } finally {
            app()->instance('env', $previousEnvironment);
        }
    }

    public function test_case_reference_and_type_cannot_be_changed_after_creation(): void
    {
        $case = $this->feedback();
        $this->expectException(ValidationException::class);
        $case->type = 'excursion';
        $case->save();
    }

    public function test_assigned_editor_cannot_edit_another_section_case_by_direct_model_call(): void
    {
        $section = $this->section('assigned-section');
        $editor = $this->editor();
        $section->editors()->attach($editor->id);
        $case = $this->feedback(['museum_section_id' => $section->id, 'assigned_to_id' => $editor->id]);
        $this->actingAs($editor, 'moonshine');
        $this->expectException(AuthorizationException::class);
        $case->update(['topic' => 'visit']);
    }

    public function test_no_public_intake_or_private_case_data_in_public_export(): void
    {
        $case = $this->feedback();
        $this->post('/api/museum-requests', [
            'email' => 'person@example.invalid', 'message' => 'Hello',
        ])->assertNotFound();
        $this->post('/museum-requests', ['email' => 'person@example.invalid'])
            ->assertNotFound();

        $out = storage_path('framework/testing/requests-no-leak.json');
        $manifest = storage_path('framework/testing/requests-no-leak-manifest.json');
        try {
            $this->artisan('museum:export', [
                '--output' => $out, '--manifest' => $manifest,
            ])->assertSuccessful();
            $snapshot = file_get_contents($out);
            $this->assertStringNotContainsString($case->reference, $snapshot);
            $this->assertStringNotContainsString('museum_requests', $snapshot);
            $this->assertStringNotContainsString('request_transitions', $snapshot);
        } finally {
            @unlink($out);
            @unlink($manifest);
        }
    }

    public function test_section_with_case_cannot_be_deleted(): void
    {
        $section = $this->section('request-section');
        $this->feedback(['museum_section_id' => $section->id]);
        $this->expectException(ValidationException::class);
        $section->delete();
    }
}
