<?php

namespace Tests\Feature;

use App\Models\MuseumEntry;
use Illuminate\Foundation\Testing\RefreshDatabase;
use MoonShine\Laravel\Models\MoonshineUser;
use MoonShine\Laravel\Models\MoonshineUserRole;
use Tests\TestCase;

class EditorialPublicationJourneyTest extends TestCase
{
    use RefreshDatabase;

    public function test_editor_ui_submits_material_then_only_public_records_reach_static_export(): void
    {
        $editorRole = MoonshineUserRole::query()->where('name', 'Editor')->firstOrFail();
        $editor = MoonshineUser::factory()->create(['moonshine_user_role_id' => $editorRole->id]);

        $this->actingAs($editor, 'moonshine');

        foreach ([['private-draft', 'draft'], ['approved-news', 'published']] as [$slug, $status]) {
            $this->post('/admin/resource/museum-entry-resource/crud', [
                'type' => 'news',
                'slug' => $slug,
                'title' => 'Тестовый материал '.$slug,
                'body' => 'Демо-текст новости',
                'excerpt' => 'Анонс',
                'status' => $status,
                'seo_title' => 'SEO',
            ])->assertRedirect();
        }

        $this->assertSame(2, MuseumEntry::count());
        $this->assertSame(1, MuseumEntry::public()->count());

        $output = storage_path('framework/testing/editorial.json');
        $manifest = storage_path('framework/testing/editorial-manifest.json');

        try {
            $this->artisan('museum:export', ['--output' => $output, '--manifest' => $manifest])
                ->assertSuccessful();
            $snapshot = json_decode(file_get_contents($output), true, flags: JSON_THROW_ON_ERROR);
            $this->assertSame(['approved-news'], array_column($snapshot['entries'], 'slug'));
            $this->assertStringNotContainsString('private-draft', file_get_contents($output));
            $this->assertSame(
                hash_file('sha256', $output),
                json_decode(file_get_contents($manifest), true)['files']['published.json']['sha256']
            );
        } finally {
            @unlink($output);
            @unlink($manifest);
        }
    }
}
