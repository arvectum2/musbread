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

    public function test_gif_upload_is_safely_flattened_to_first_frame_webp(): void
    {
        Storage::fake('local');
        $entry = $this->entry();
        $this->actingAs(MoonshineUser::factory()->create(), 'moonshine');
        $response = $this->post('/admin/museum-media', [
            'museum_entry_id' => $entry->id,
            'alt' => 'Первый кадр исторической анимации (демо)',
            'image' => UploadedFile::fake()->image('photo.gif', 40, 30),
        ]);
        $response->assertRedirect();
        $media = MuseumMedia::firstOrFail();
        $this->assertSame('image/webp', $media->mime);
        $this->assertSame(IMAGETYPE_WEBP,
            getimagesizefromstring(Storage::disk('local')->get($media->storage_path))[2]);
    }

    private function animatedGif(int $frames = 2, int $delay = 10): string
    {
        // Native GIF89a: two colours, 1x1 pixels; no external fixture libraries.
        $gif = 'GIF89a'.pack('v2', 1, 1)."\x80\x00\x00"."\x00\x00\x00\xff\xff\xff";
        $gif .= "\x21\xff\x0bNETSCAPE2.0\x03\x01\x00\x00\x00";
        for ($index = 0; $index < $frames; ++$index) {
            $gif .= "\x21\xf9\x04\x00".pack('v',$delay)."\x00\x00";
            $gif .= "\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00";
            $gif .= "\x02\x02".($index % 2 ? "\x4c\x01" : "\x44\x01")."\x00";
        }
        return $gif."\x3b";
    }

    public function test_animated_gif_remains_animated_in_safe_public_webp_with_two_frames(): void
    {
        Storage::fake('local');
        $entry = $this->entry('published');
        $this->actingAs(MoonshineUser::factory()->create(), 'moonshine');
        $input = $this->animatedGif();
        $this->assertSame(IMAGETYPE_GIF, getimagesizefromstring($input)[2]);
        $this->post('/admin/museum-media', [
            'museum_entry_id' => $entry->id,
            'alt' => 'Два сменяющихся кадра музейной схемы',
            'image' => UploadedFile::fake()->createWithContent('animation.gif', $input),
        ])->assertRedirect(route('museum.media.index'));
        $media = MuseumMedia::firstOrFail();
        $clean = Storage::disk('local')->get($media->storage_path);
        $this->assertSame('image/webp', $media->mime);
        $this->assertSame('WEBP', substr($clean,8,4));
        $this->assertStringContainsString('ANIM', $clean);
        $this->assertSame(2, substr_count($clean, 'ANMF'));
        $this->assertSame(IMAGETYPE_WEBP, getimagesizefromstring($clean)[2]);
        $this->assertSame(hash('sha256',$clean), $media->sha256);
        $this->assertStringNotContainsString('NETSCAPE2.0', $clean);
        $this->get(route('museum.media.preview', $media))
            ->assertOk()->assertHeader('Content-Type','image/webp');
        // Public release only takes the re-encoded checksum-verified WebP.
        $dir = storage_path('framework/testing/animated-tz182-'.bin2hex(random_bytes(3)));
        $out = storage_path('framework/testing/tz182-animated-export.json');
        $manifest = storage_path('framework/testing/tz182-animated-manifest.json');
        try {
            $this->artisan('museum:export',[ '--output'=>$out, '--manifest'=>$manifest, '--media-output-dir'=>$dir])->assertSuccessful();
            $data = json_decode(file_get_contents($out),true,flags:JSON_THROW_ON_ERROR);
            $this->assertCount(1,$data['entries'][0]['media']);
            $this->assertSame('/media/'.$media->sha256.'.webp',$data['entries'][0]['media'][0]['src']);
            $published = file_get_contents($dir.'/'.$media->sha256.'.webp');
            $this->assertSame($clean,$published);
            $this->assertSame(2,substr_count($published,'ANMF'));
        } finally {
            @unlink($out);@unlink($manifest);
            foreach (glob($dir.'/*') ?: [] as $file) @unlink($file);
            @rmdir($dir);
        }
    }

    public function test_large_static_gif_retains_preexisting_allowed_upload_dimensions(): void
    {
        Storage::fake('local');
        $entry=$this->entry();
        $this->actingAs(MoonshineUser::factory()->create(),'moonshine');
        $this->post('/admin/museum-media', [
            'museum_entry_id'=>$entry->id,
            'alt'=>'Стационарная панорама экспозиционного пространства',
            'image'=>UploadedFile::fake()->image('large-static.gif', 1300, 100),
        ])->assertRedirect(route('museum.media.index'));
        $media=MuseumMedia::firstOrFail();
        $this->assertSame(1300, $media->width);
        $this->assertSame(100, $media->height);
        $this->assertSame(IMAGETYPE_WEBP, getimagesizefromstring(Storage::disk('local')->get($media->storage_path))[2]);
    }

    public function test_invalid_excessive_and_trailing_gif_animation_fails_closed(): void
    {
        Storage::fake('local');
        $entry=$this->entry();
        $this->actingAs(MoonshineUser::factory()->create(),'moonshine');
        foreach ([$this->animatedGif(61), $this->animatedGif(2, 1600),
                   $this->animatedGif()."<script>malicious</script>",
                   substr($this->animatedGif(), 0, -1),
        ] as $index=>$bytes) {
            $this->post('/admin/museum-media',[
                'museum_entry_id'=>$entry->id,
                'alt'=>'Неприемлемый анимированный файл',
                'image'=>UploadedFile::fake()->createWithContent('invalid'.$index.'.gif',$bytes),
            ])->assertSessionHasErrors('image');
        }
        $this->assertDatabaseCount('museum_media',0);
    }

    public function test_editor_cannot_view_modify_or_remove_media_from_other_section(): void
    {
        Storage::fake('local');
        $own = \App\Models\MuseumSection::create([
            'slug' => 'editable-images', 'title' => 'Свой', 'status' => 'published',
        ]);
        $restricted = \App\Models\MuseumSection::create([
            'slug' => 'secret-images', 'title' => 'Чужой', 'status' => 'published',
        ]);
        $entry = $this->entry();
        $entry->update(['museum_section_id' => $restricted->id]);
        $role = \MoonShine\Laravel\Models\MoonshineUserRole::where('name', 'Editor')->firstOrFail();
        $editor = MoonshineUser::factory()->create(['moonshine_user_role_id' => $role->id]);
        $own->editors()->attach($editor->id);

        $this->actingAs(MoonshineUser::factory()->create(), 'moonshine')
            ->post('/admin/museum-media', [
                'museum_entry_id' => $entry->id, 'alt' => 'Не показывать этому редактору',
                'image' => UploadedFile::fake()->image('secret.png', 25, 25),
            ])->assertRedirect();
        $item = MuseumMedia::firstOrFail();

        $this->actingAs($editor, 'moonshine');
        $this->get('/admin/museum-media')->assertOk()->assertDontSee('Не показывать этому редактору');
        $this->get(route('museum.media.preview', $item))->assertForbidden();
        $this->delete(route('museum.media.destroy', $item))->assertForbidden();
        $this->patch(route('museum.media.update', $item), [
            'museum_entry_id' => $entry->id, 'alt' => 'Подмена чужого alt',
        ])->assertForbidden();
        $this->assertDatabaseCount('museum_media', 1);
    }

    public function test_safe_svg_is_rasterized_to_webp_without_publishing_svg_source(): void
    {
        Storage::fake('local');
        $entry = $this->entry('published');
        $this->actingAs(MoonshineUser::factory()->create(), 'moonshine');
        $svg = '<svg xmlns="http://www.w3.org/2000/svg" width="80" height="60" viewBox="0 0 80 60">'
            .'<rect width="80" height="60" fill="#197e87"/>'
            .'<circle cx="32" cy="30" r="15" fill="white"/></svg>';
        $this->post('/admin/museum-media', [
            'museum_entry_id' => $entry->id, 'alt' => 'Схематическое зерно внутри круга',
            'image' => UploadedFile::fake()->createWithContent('diagram.svg', $svg),
        ])->assertRedirect(route('museum.media.index'));
        $item = MuseumMedia::firstOrFail();
        $this->assertSame('image/webp', $item->mime);
        $this->assertSame(80, $item->width);
        $this->assertSame(60, $item->height);
        $this->assertSame(IMAGETYPE_WEBP,
            getimagesizefromstring(Storage::disk('local')->get($item->storage_path))[2]);
        $this->assertStringNotContainsString('<svg', Storage::disk('local')->get($item->storage_path));
    }

    public function test_svg_scripts_external_refs_doctype_and_embedded_images_are_rejected(): void
    {
        Storage::fake('local');
        $entry = $this->entry();
        $this->actingAs(MoonshineUser::factory()->create(), 'moonshine');
        $payloads = [
            '<svg xmlns="http://www.w3.org/2000/svg" width="80" height="60"><script>alert(1)</script></svg>',
            '<svg xmlns="http://www.w3.org/2000/svg" width="80" height="60"><image href="https://external.example/pic.png"/></svg>',
            '<!DOCTYPE svg [<!ENTITY xxe SYSTEM "file:///etc/passwd">]><svg xmlns="http://www.w3.org/2000/svg" width="80" height="60">&xxe;</svg>',
            '<svg xmlns="http://www.w3.org/2000/svg" width="80" height="60"><rect width="80" height="60" fill="url(https://evil.example/a)"/></svg>',
            '<svg xmlns="http://www.w3.org/2000/svg" width="80" height="60"><foreignObject><p>bad</p></foreignObject></svg>',
            '<svg xmlns="http://www.w3.org/2000/svg" width="5000" height="60"><rect width="10" height="10"/></svg>',
        ];
        foreach ($payloads as $index => $svg) {
            $this->post('/admin/museum-media', [
                'museum_entry_id' => $entry->id, 'alt' => 'Попытка загрузить опасный SVG',
                'image' => UploadedFile::fake()->createWithContent('bad'.$index.'.svg', $svg),
            ])->assertSessionHasErrors('image');
        }
        $this->assertDatabaseCount('museum_media', 0);
    }

    public function test_editor_can_access_media_library(): void
    {
        $roleId = \MoonShine\Laravel\Models\MoonshineUserRole::where('name', 'Editor')->firstOrFail()->id;
        $editor = MoonshineUser::factory()->create(['moonshine_user_role_id' => $roleId]);
        $this->actingAs($editor, 'moonshine')->get('/admin/museum-media')->assertOk();
    }
}
