<?php

namespace Tests\Feature;

use App\Models\MuseumAuditRecord;
use App\Models\MuseumEntry;
use App\Models\MuseumMedia;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Http\UploadedFile;
use Illuminate\Support\Facades\Storage;
use MoonShine\Laravel\Models\MoonshineUser;
use Tests\TestCase;

class MuseumMediaTest extends TestCase
{
    use RefreshDatabase;

    private function entry(string $status = 'draft'): MuseumEntry
    {
        return MuseumEntry::create([
            'type' => 'news', 'slug' => 'image-news', 'title' => 'Новость с иллюстрацией',
            'body' => 'Демонстрационная новость', 'status' => $status,
        ]);
    }

    public function test_guest_cannot_view_upload_or_preview_media(): void
    {
        $this->get('/admin/museum-media')->assertRedirect('/admin/login');
        $this->post('/admin/museum-media', ['alt' => 'Изображение'])->assertRedirect('/admin/login');

        $this->assertSame(0, MuseumMedia::count());
    }

    public function test_editor_upload_reencodes_and_secures_media(): void
    {
        Storage::fake('local');
        $entry = $this->entry();
        $admin = MoonshineUser::factory()->create();
        $this->actingAs($admin, 'moonshine');
        $this->get('/admin/museum-media')->assertOk();

        $this->post('/admin/museum-media', [
            'museum_entry_id' => $entry->id,
            'alt' => 'Иллюстрация тестового музейного зала',
            'caption' => 'Демонстрационный образец',
            'image' => UploadedFile::fake()->image('original.png', 120, 80),
        ])->assertRedirect(route('museum.media.index'));

        $this->assertSame(1, MuseumMedia::count());
        $media = MuseumMedia::firstOrFail();
        $this->assertSame('image/webp', $media->mime);
        $this->assertSame($entry->id, $media->museum_entry_id);
        $this->assertSame($admin->id, $media->uploaded_by);
        $this->assertSame(120, $media->width);
        $this->assertSame(80, $media->height);
        $this->assertMatchesRegularExpression('/^museum\/media\/[0-9a-f-]+\.webp$/', $media->storage_path);

        Storage::disk('local')->assertExists($media->storage_path);
        $contents = Storage::disk('local')->get($media->storage_path);
        $this->assertSame(IMAGETYPE_WEBP, getimagesizefromstring($contents)[2]);
        $this->assertSame(hash('sha256', $contents), $media->sha256);
        $this->get(route('museum.media.preview', $media))
            ->assertOk()->assertHeader('Content-Type', 'image/webp');

        $this->assertDatabaseHas('museum_audit_records', [
            'subject_type' => 'MuseumMedia', 'subject_id' => $media->id, 'action' => 'created',
        ]);
        $this->delete(route('museum.media.destroy', $media))->assertRedirect();
        Storage::disk('local')->assertMissing($media->storage_path);
        $this->assertSame(0, MuseumMedia::count());
    }

    public function test_invalid_files_and_missing_alt_are_rejected(): void
    {
        Storage::fake('local');
        $entry = $this->entry();
        $this->actingAs(MoonshineUser::factory()->create(), 'moonshine');

        $this->post('/admin/museum-media', [
            'museum_entry_id' => $entry->id, 'alt' => 'Альт',
            'image' => UploadedFile::fake()->createWithContent('script.svg', '<svg onload="evil()"></svg>'),
        ])->assertSessionHasErrors('image');

        $this->post('/admin/museum-media', [
            'museum_entry_id' => $entry->id, 'alt' => '',
            'image' => UploadedFile::fake()->image('test.png'),
        ])->assertSessionHasErrors('alt');

        $this->post('/admin/museum-media', [
            'museum_entry_id' => $entry->id, 'alt' => 'Большое изображение',
            'image' => UploadedFile::fake()->image('oversized.png', 4097, 20),
        ])->assertSessionHasErrors('image');

        $this->assertSame(0, MuseumMedia::count());
    }

    public function test_only_published_entries_export_media_with_verified_digest(): void
    {
        Storage::fake('local');
        $published = $this->entry();
        $hidden = MuseumEntry::create([
            'type' => 'page', 'slug' => 'hidden-entry', 'title' => 'Скрытый материал',
            'body' => 'Тест', 'status' => 'draft',
        ]);
        $this->actingAs(MoonshineUser::factory()->create(), 'moonshine');

        foreach ([$published, $hidden] as $entry) {
            $this->post('/admin/museum-media', [
                'museum_entry_id' => $entry->id, 'alt' => 'Надёжное описание изображения',
                'image' => UploadedFile::fake()->image('photo-'.$entry->id.'.png', 25, 25),
            ])->assertRedirect();
        }
        $published->update(['status' => 'published']);

        $dir = storage_path('framework/testing/exported-media-'.uniqid());
        $out = storage_path('framework/testing/media-export.json');
        $manifest = storage_path('framework/testing/media-export-manifest.json');
        try {
            $this->artisan('museum:export', [
                '--output' => $out, '--manifest' => $manifest, '--media-output-dir' => $dir,
            ])->assertSuccessful();

            $snapshot = json_decode(file_get_contents($out), true, flags: JSON_THROW_ON_ERROR);
            $this->assertSame(['image-news'], array_column($snapshot['entries'], 'slug'));
            $this->assertCount(1, $snapshot['entries'][0]['media']);
            $record = $snapshot['entries'][0]['media'][0];
            $this->assertSame('Надёжное описание изображения', $record['alt']);
            $this->assertStringStartsWith('/media/', $record['src']);
            $this->assertStringNotContainsString('hidden-entry', file_get_contents($out));
            $this->assertStringNotContainsString('uploaded_by', file_get_contents($out));

            $filename = basename($record['src']);
            $assetPath = $dir.'/'.$filename;
            $this->assertFileExists($assetPath);
            $audit = json_decode(file_get_contents($manifest), true, flags: JSON_THROW_ON_ERROR);
            $this->assertSame(
                hash_file('sha256', $assetPath),
                $audit['files']['media/'.$filename]['sha256']
            );

            $published->update(['status' => 'draft']);
            $this->artisan('museum:export', [
                '--output' => $out, '--manifest' => $manifest, '--media-output-dir' => $dir,
            ])->assertSuccessful();
            $this->assertFileDoesNotExist($assetPath);
            $this->assertCount(0, json_decode(file_get_contents($out), true)['entries']);
        } finally {
            @unlink($out);
            @unlink($manifest);
            foreach (glob($dir.'/*') ?: [] as $path) @unlink($path);
            @rmdir($dir);
        }
    }

    public function test_media_alt_caption_and_entry_link_can_be_updated(): void
    {
        Storage::fake('local');
        $old = $this->entry('published');
        $next = MuseumEntry::create([
            'type' => 'page', 'slug' => 'new-gallery', 'title' => 'Новая галерея',
            'body' => 'Текст', 'status' => 'draft',
        ]);
        $this->actingAs(MoonshineUser::factory()->create(), 'moonshine');
        $this->post('/admin/museum-media', [
            'museum_entry_id' => $old->id, 'alt' => 'Изначальная подпись',
            'image' => UploadedFile::fake()->image('test.png', 40, 30),
        ])->assertRedirect();

        $media = MuseumMedia::firstOrFail();
        $this->patch(route('museum.media.update', $media), [
            'museum_entry_id' => $next->id,
            'alt' => 'Исправленное описание изображения',
            'caption' => 'Новая подпись',
        ])->assertRedirect();
        $this->assertDatabaseHas('museum_media', [
            'id' => $media->id, 'museum_entry_id' => $next->id,
            'alt' => 'Исправленное описание изображения',
            'caption' => 'Новая подпись',
        ]);
        $this->assertDatabaseHas('museum_audit_records', [
            'subject_type' => 'MuseumMedia',
            'subject_id' => $media->id,
            'action' => 'updated',
        ]);
        $this->patch(route('museum.media.update', $media), [
            'museum_entry_id' => $next->id, 'alt' => '',
        ])->assertSessionHasErrors('alt');
    }

    public function test_tampered_private_file_aborts_public_export(): void
    {
        Storage::fake('local');
        $entry = $this->entry('published');
        $this->actingAs(MoonshineUser::factory()->create(), 'moonshine');
        $this->post('/admin/museum-media', [
            'museum_entry_id' => $entry->id, 'alt' => 'Проверка целостности',
            'image' => UploadedFile::fake()->image('intact.jpg', 20, 20),
        ])->assertRedirect();
        $media = MuseumMedia::firstOrFail();
        Storage::disk('local')->put($media->storage_path, 'tampered-file');

        $out = storage_path('framework/testing/tamper-export.json');
        $manifest = storage_path('framework/testing/tamper-manifest.json');
        try {
            try {
                $this->artisan('museum:export', ['--output' => $out, '--manifest' => $manifest]);
                $this->fail('Tampered media must not export');
            } catch (\RuntimeException $exception) {
                $this->assertStringContainsString('checksum', $exception->getMessage());
            }
            $this->assertFileDoesNotExist($out);
        } finally {
            @unlink($out);
            @unlink($manifest);
        }
    }

    public function test_editor_can_access_media_library(): void
    {
        $roleId = \MoonShine\Laravel\Models\MoonshineUserRole::where('name', 'Editor')->firstOrFail()->id;
        $editor = MoonshineUser::factory()->create(['moonshine_user_role_id' => $roleId]);
        $this->actingAs($editor, 'moonshine')->get('/admin/museum-media')->assertOk();
    }
}
