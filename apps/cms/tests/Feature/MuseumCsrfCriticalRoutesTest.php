<?php

namespace Tests\Feature;

use App\Models\MuseumEntry;
use Illuminate\Foundation\Testing\RefreshDatabase;
use MoonShine\Laravel\Models\MoonshineUser;
use Tests\TestCase;

/** Run real CSRF middleware by temporarily disabling Laravel's testing bypass. */
final class MuseumCsrfCriticalRoutesTest extends TestCase
{
    use RefreshDatabase;

    private function productionCsrf(callable $check): void
    {
        $old = app()->environment();
        app()->instance('env', 'production');
        try { $check(); } finally { app()->instance('env', $old); }
    }

    public function test_invalid_token_blocks_all_critical_cms_post_routes(): void
    {
        $admin = MoonshineUser::factory()->create();
        $entry = MuseumEntry::create([
            'type' => 'news', 'slug' => 'csrf-security-probe',
            'title' => 'Тестовая новость', 'body' => '<p>Музейный текст</p>',
            'status' => 'draft',
        ]);
        $this->productionCsrf(function () use ($admin, $entry): void {
            $this->actingAs($admin, 'moonshine')
                ->withSession(['_token' => 'correct-session-token'])
                ->withHeader('Sec-Fetch-Site', 'cross-site');
            foreach ([
                '/admin/museum-documents',
                '/admin/museum-media',
                '/admin/museum-media/suggest-alt',
                '/admin/museum-content/queue-publication',
                '/admin/museum-entries/'.$entry->id.'/approve-and-queue',
                '/admin/museum-content/review-notes',
            ] as $url) {
                $this->post($url, [
                    '_token' => 'forged-cross-site-token',
                    'museum_entry_id' => $entry->id,
                ])->assertStatus(419);
            }
        });
        $this->assertDatabaseCount('museum_documents', 0);
        $this->assertDatabaseCount('museum_media', 0);
        $this->assertDatabaseCount('museum_publication_runs', 0);
    }

    public function test_forged_token_blocks_document_review_and_file_deletion(): void
    {
        $admin = MoonshineUser::factory()->create();
        $this->productionCsrf(function () use ($admin): void {
            $this->actingAs($admin, 'moonshine')
                ->withSession(['_token' => 'real-session-csrf'])
                ->withHeader('Sec-Fetch-Site', 'cross-site');
            $this->patch('/admin/museum-documents/123456/accessibility', [
                '_token' => 'forged-session-csrf',
                'accessibility_reviewed' => true,
            ])->assertStatus(419);
            $this->patch('/admin/museum-documents/123456/accessible-edition', [
                '_token' => 'forged-session-csrf',
                'approve_equivalence' => true,
            ])->assertStatus(419);
            $this->delete('/admin/museum-documents/123456', [
                '_token' => 'forged-session-csrf',
            ])->assertStatus(419);
            $this->delete('/admin/museum-media/123456', [
                '_token' => 'forged-session-csrf',
            ])->assertStatus(419);
        });
        $this->assertDatabaseCount('museum_documents', 0);
    }

    public function test_valid_session_token_allows_private_alt_suggestion_without_publishing(): void
    {
        $admin = MoonshineUser::factory()->create();
        $entry = MuseumEntry::create([
            'type' => 'news', 'slug' => 'csrf-valid-suggestion',
            'title' => 'Тест подписи', 'body' => '<p>Музейный экспонат</p>',
            'status' => 'draft',
        ]);
        $this->productionCsrf(function () use ($admin, $entry): void {
            $this->actingAs($admin, 'moonshine')
                ->withSession(['_token' => 'valid-session-token'])
                ->withHeader('Sec-Fetch-Site', 'cross-site')
                ->post('/admin/museum-media/suggest-alt', [
                    '_token' => 'valid-session-token',
                    'museum_entry_id' => $entry->id,
                    'caption' => 'Музейная витрина с исторической посудой и подписью',
                ])->assertOk()->assertJsonPath('review_required', true);
        });
        $this->assertDatabaseCount('museum_media', 0);
    }
}
