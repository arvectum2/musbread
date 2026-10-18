<?php

declare(strict_types=1);

namespace Tests\Feature;

use App\Models\MuseumEntry;
use App\Models\MuseumEvent;
use App\Models\MuseumMedia;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Artisan;
use Illuminate\Support\Facades\Storage;
use Illuminate\Http\UploadedFile;
use Tests\TestCase;

final class ImportOfficialMuseumPhotosTest extends TestCase
{
    use RefreshDatabase;

    private array $created=[];

    protected function tearDown():void
    {
        foreach($this->created as $filename) {
            if(is_dir($filename)) @rmdir($filename);
            else @unlink($filename);
        }
        parent::tearDown();
    }

    private function originalManifest(bool $tamper=false):string
    {
        $capture=json_decode((string)file_get_contents(
            base_path('../web/src/data/official-workshop-pages.json')),true);
        $item=$capture['programs'][0];
        $src=$item['image_links'][0];
        $original=preg_replace('~^https://muzei-xleb\.ru/sites/default/files/styles/[^/]+/public/~',
                              'https://muzei-xleb.ru/sites/default/files/',$src['url']);
        $original=explode('?',$original,2)[0];
        $image=UploadedFile::fake()->image('source-photo.jpg',120,85);
        $raw=(string)file_get_contents($image->getRealPath());
        $sha=hash('sha256',$raw);
        $dir=storage_path('framework/testing/original-photo-museum-'.uniqid());
        mkdir($dir,0700,true);
        $file=$dir.'/'.$sha.'.jpg';
        file_put_contents($file,$raw);
        $this->created[]=$file;
        $manifest=[
            'source'=>'https://muzei-xleb.ru',
            'rights_status'=>'not-verified-private-only',
            'files'=>[[
                'cms_slug'=>$item['slug'],
                'title'=>$item['title'],
                'source_page_url'=>$item['source_url'],
                'source_image_url'=>$src['url'],
                'original_url'=>$original,
                'source_alt'=>$src['alt'],
                'source_snapshot'=>'official-workshop-pages.json',
                'source_html_sha256'=>$item['html_sha256'],
                'sha256'=>$tamper ? str_repeat('0',64) : $sha,
                'local_name'=>$sha.'.jpg',
                'size_bytes'=>strlen($raw),
                'format'=>'jpg',
            ]],
        ];
        $path=$dir.'/manifest.json';
        file_put_contents($path,json_encode($manifest,JSON_UNESCAPED_UNICODE));
        $this->created[]=$path;
        $this->created[]=$dir;
        return $path;
    }

    private function owner():MuseumEntry
    {
        return MuseumEntry::create([
            'slug'=>'museum-workshop-kukly-kuvadki',
            'type'=>'page',
            'title'=>'«Кувадка»',
            'body'=>'<p>Подлинный музейный мастер-класс.</p>',
            'status'=>'draft',
        ]);
    }

    public function test_original_museum_photo_import_is_idempotent_and_private():void
    {
        Storage::fake('local');
        $entry=$this->owner();
        $path=$this->originalManifest();
        $this->assertSame(0,Artisan::call('museum:import-official-photos',
            ['--manifest'=>$path]),Artisan::output());
        $this->assertDatabaseCount('museum_media',0);

        $this->assertSame(0,Artisan::call('museum:import-official-photos',
            ['--apply'=>true,'--manifest'=>$path]),Artisan::output());
        $this->assertDatabaseCount('museum_media',1);
        $record=MuseumMedia::firstOrFail();
        $this->assertTrue($record->source_rights_pending);
        $this->assertSame($entry->id,$record->museum_entry_id);
        $this->assertSame('image/webp',$record->mime);
        $this->assertStringStartsWith('https://muzei-xleb.ru/sites/default/files/',$record->source_original_url);
        $this->assertSame(64,strlen($record->source_original_sha256));
        Storage::disk('local')->assertExists($record->storage_path);
        $this->assertSame(hash('sha256',Storage::disk('local')->get($record->storage_path)),
            $record->sha256);

        $this->assertSame(0,Artisan::call('museum:import-official-photos',
            ['--apply'=>true,'--manifest'=>$path]),Artisan::output());
        $this->assertDatabaseCount('museum_media',1);

        // Critical: even publishing the parent must NOT leak rights-pending
        // original media, including the bytes in the exported media directory.
        $entry->update(['status'=>'published']);
        // Same rights-pending museum photo must not be smuggled in as an
        // event cover when the event itself has been approved.
        $blocked=[
            'slug'=>'qa-museum-photo-event',
            'title'=>'Тестовая программа',
            'category'=>'Мастер-классы',
            'starts_at'=>'2026-11-18 10:00:00',
            'status'=>'published',
            'published_at'=>now()->subMinutes(2),
            'cover_media_id'=>$record->id,
            'body'=>'<p>Синтетический тест, не музейный анонс</p>',
            'excerpt'=>'Короткий искусственный анонс только для QA',
        ];
        try {
            MuseumEvent::create($blocked);
            $this->fail('Source-rights pending museum photo must not be selectable as event cover');
        } catch (\Illuminate\Validation\ValidationException $e) {
            $this->assertArrayHasKey('cover_media_id',$e->errors());
        }
        $blocked['cover_media_id']=null;
        $event=MuseumEvent::create($blocked);
        \Illuminate\Support\Facades\DB::table('museum_events')
            ->where('id',$event->id)->update(['cover_media_id'=>$record->id]);
        $base=storage_path('framework/testing/photo-rights-'.$record->id);
        try {
            $this->assertSame(0,Artisan::call('museum:export',[
                '--output'=>$base.'.json',
                '--manifest'=>$base.'.manifest.json',
                '--media-output-dir'=>$base.'-media',
                '--document-output-dir'=>$base.'-docs',
            ]),Artisan::output());
            $data=json_decode((string)file_get_contents($base.'.json'),true);
            $this->assertSame($entry->slug,$data['entries'][0]['slug']);
            $this->assertArrayNotHasKey('media',$data['entries'][0]);
            $this->assertFalse(is_file($base.'-media/'.$record->sha256.'.webp'));
            $this->assertStringNotContainsString($record->source_original_url,
                (string)file_get_contents($base.'.json'));
            $this->assertCount(1,$data['events']);
            $this->assertSame($event->slug,$data['events'][0]['slug']);
            $this->assertArrayNotHasKey('cover_image',$data['events'][0]);
        } finally {
            @unlink($base.'.json');@unlink($base.'.manifest.json');
            foreach(glob($base.'-media/*')?:[] as $f)@unlink($f);
            @rmdir($base.'-media');
            foreach(glob($base.'-docs/*')?:[] as $f)@unlink($f);
            @rmdir($base.'-docs');
        }
    }

    public function test_two_original_gallery_images_attach_to_same_workshop_without_duplicates():void
    {
        Storage::fake('local');
        $owner=$this->owner();
        $path=$this->originalManifest();
        $manifest=json_decode((string)file_get_contents($path),true);
        $capture=json_decode((string)file_get_contents(
            base_path('../web/src/data/official-workshop-pages.json')),true);
        $second=$capture['programs'][0]['image_links'][1];
        $secondPhoto=UploadedFile::fake()->image('genuine-gallery-test.jpg',88,56);
        $raw=(string)file_get_contents($secondPhoto->getRealPath());
        $digest=hash('sha256',$raw);
        $file=dirname($path).'/'.$digest.'.jpg';
        file_put_contents($file,$raw);
        // Cleanup source image before the test temp directory is removed.
        array_unshift($this->created,$file);
        $extra=$manifest['files'][0];
        $extra['source_image_url']=$second['url'];
        $extra['source_image_index']=1;
        $extra['source_alt']=$second['alt'];
        $extra['original_url']=preg_replace(
            '~^https://muzei-xleb\\.ru/sites/default/files/styles/[^/]+/public/~',
            'https://muzei-xleb.ru/sites/default/files/',$second['url']);
        $extra['original_url']=explode('?',$extra['original_url'],2)[0];
        $extra['sha256']=$digest;
        $extra['local_name']=$digest.'.jpg';
        $extra['size_bytes']=strlen($raw);
        $manifest['files'][]=$extra;
        file_put_contents($path,json_encode($manifest,JSON_UNESCAPED_UNICODE));
        $this->assertSame(0,Artisan::call('museum:import-official-photos',[
            '--apply'=>true,'--manifest'=>$path,
        ]),Artisan::output());
        $this->assertSame(2,MuseumMedia::where('museum_entry_id',$owner->id)->count());
        $this->assertSame(2,MuseumMedia::where('source_rights_pending',true)->count());
        $this->assertSame(2,MuseumMedia::distinct('source_original_sha256')
            ->count('source_original_sha256'));
        $this->assertSame(0,Artisan::call('museum:import-official-photos',[
            '--apply'=>true,'--manifest'=>$path,
        ]),Artisan::output());
        $this->assertDatabaseCount('museum_media',2);
    }

    public function test_real_room_photo_matches_exact_existing_museum_room_source():void
    {
        Storage::fake('local');
        $source=json_decode((string)file_get_contents(
            base_path('../web/src/data/official-exposition-rooms.json')),true);
        $room=$source['rooms'][0];
        MuseumEntry::create([
            'slug'=>$room['slug'],'title'=>$room['title'],
            'type'=>'page','status'=>'draft','body'=>'<p>Сохранённый оригинальный зал музея.</p>',
        ]);
        $path=$this->originalManifest();
        $manifest=json_decode((string)file_get_contents($path),true);
        $photo=$room['image_sources'][0]['source_url'];
        $row=&$manifest['files'][0];
        $row['cms_slug']=$room['slug'];
        $row['title']=$room['title'];
        $row['source_page_url']=$room['source_url'];
        $row['source_image_url']=$photo;
        $row['source_snapshot']='official-exposition-rooms.json';
        $row['source_image_index']=0;
        $row['source_html_sha256']=$room['html_sha256'];
        $row['source_alt']=$room['image_sources'][0]['alt'];
        $row['original_url']=preg_replace(
            '~^https://muzei-xleb\\.ru/sites/default/files/styles/[^/]+/public/~',
            'https://muzei-xleb.ru/sites/default/files/',$photo);
        $row['original_url']=explode('?',$row['original_url'],2)[0];
        file_put_contents($path,json_encode($manifest,JSON_UNESCAPED_UNICODE));
        $this->assertSame(0,Artisan::call('museum:import-official-photos',[
            '--apply'=>true,'--manifest'=>$path,
        ]),Artisan::output());
        $this->assertDatabaseHas('museum_media',[
            'source_original_url'=>$row['original_url'],'source_rights_pending'=>1,
        ]);
        $this->assertSame($room['slug'],MuseumMedia::firstOrFail()->entry->slug);
    }

    public function test_real_exhibition_cover_must_match_exact_index_and_detail():void
    {
        Storage::fake('local');
        $source=json_decode((string)file_get_contents(
            base_path('../web/src/data/official-exhibition-details.json')),true);
        $index=json_decode((string)file_get_contents(
            base_path('../web/src/data/official-exhibition-indexes.json')),true);
        $details=$source['exhibitions'][0];
        $cover=$index['indexes'][0]['image_links'][0]['url'];
        MuseumEntry::create([
            'slug'=>$details['slug'],'title'=>$details['title'],
            'type'=>'exhibition','status'=>'draft','body'=>'<p>Тестовый исходный музейный анонс.</p>',
        ]);
        $path=$this->originalManifest();
        $manifest=json_decode((string)file_get_contents($path),true);
        $row=&$manifest['files'][0];
        $row['cms_slug']=$details['slug'];
        $row['title']=$details['title'];
        $row['source_page_url']=$details['source_url'];
        $row['source_image_url']=$cover;
        $row['source_snapshot']='official-exhibition-indexes.json';
        $row['source_image_index']=0;
        $row['source_html_sha256']=$details['html_sha256'];
        $row['source_alt']=$index['indexes'][0]['image_links'][0]['alt'];
        $row['original_url']=preg_replace(
            '~^https://muzei-xleb\\.ru/sites/default/files/styles/[^/]+/public/~',
            'https://muzei-xleb.ru/sites/default/files/',$cover);
        $row['original_url']=explode('?',$row['original_url'],2)[0];
        file_put_contents($path,json_encode($manifest,JSON_UNESCAPED_UNICODE));
        $this->assertSame(0,Artisan::call('museum:import-official-photos',[
            '--apply'=>true,'--manifest'=>$path,
        ]),Artisan::output());
        $this->assertDatabaseHas('museum_media',[
            'source_original_url'=>$row['original_url'],'source_rights_pending'=>1,
        ]);
        $this->assertSame($details['slug'],MuseumMedia::firstOrFail()->entry->slug);

        $row['source_page_url']='https://muzei-xleb.ru/vistavky/other';
        file_put_contents($path,json_encode($manifest,JSON_UNESCAPED_UNICODE));
        $this->assertSame(1,Artisan::call('museum:import-official-photos',[
            '--apply'=>true,'--manifest'=>$path,
        ]));
        $this->assertDatabaseCount('museum_media',1);
    }

    public function test_same_actual_original_bytes_at_two_different_museum_urls_keep_both_pages():void
    {
        Storage::fake('local');
        $this->owner();
        $path=$this->originalManifest();
        $manifest=json_decode((string)file_get_contents($path),true);
        $capture=json_decode((string)file_get_contents(
            base_path('../web/src/data/official-workshop-pages.json')),true);
        $other=$capture['programs'][1];
        MuseumEntry::create([
            'slug'=>$other['slug'],
            'title'=>$other['title'],
            'type'=>'page',
            'body'=>'<p>Исходная страница музея для автоматического QA.</p>',
            'status'=>'draft',
        ]);
        $picture=$other['image_links'][0];
        $record=$manifest['files'][0];
        $record['cms_slug']=$other['slug'];
        $record['title']=$other['title'];
        $record['source_page_url']=$other['source_url'];
        $record['source_image_url']=$picture['url'];
        $record['source_alt']=$picture['alt'];
        $record['source_html_sha256']=$other['html_sha256'];
        $record['original_url']=preg_replace(
            '~^https://muzei-xleb\\.ru/sites/default/files/styles/[^/]+/public/~',
            'https://muzei-xleb.ru/sites/default/files/',$picture['url']);
        $record['original_url']=explode('?',$record['original_url'],2)[0];
        // Mimic a genuine site using the SAME original image bytes under
        // separate source URLs, as the museum does for two real excursions.
        $manifest['files'][]=$record;
        file_put_contents($path,json_encode($manifest,JSON_UNESCAPED_UNICODE));
        $this->assertSame(0,Artisan::call('museum:import-official-photos',[
            '--apply'=>true,'--manifest'=>$path,
        ]),Artisan::output());
        $this->assertDatabaseCount('museum_media',2);
        $this->assertSame(2,MuseumMedia::distinct()->count('source_original_url'));
        $this->assertSame(1,MuseumMedia::distinct()->count('sha256'));
        $this->assertSame(2,MuseumMedia::where('source_rights_pending',true)->count());
        $this->assertSame(0,Artisan::call('museum:import-official-photos',[
            '--apply'=>true,'--manifest'=>$path,
        ]),Artisan::output());
        $this->assertDatabaseCount('museum_media',2);
    }

    public function test_changed_original_jpeg_sha_blocks_import():void
    {
        Storage::fake('local');
        $this->owner();
        $path=$this->originalManifest(tamper:true);
        $this->assertSame(1,Artisan::call('museum:import-official-photos',
            ['--apply'=>true,'--manifest'=>$path]));
        $this->assertDatabaseCount('museum_media',0);
    }

    public function test_source_photo_cannot_be_mislabeled_to_a_published_or_other_entry():void
    {
        Storage::fake('local');
        $entry=$this->owner();
        $path=$this->originalManifest();
        $entry->update(['status'=>'published']);
        $this->assertSame(1,Artisan::call('museum:import-official-photos',
            ['--apply'=>true,'--manifest'=>$path]));
        $this->assertDatabaseCount('museum_media',0);
    }
}
