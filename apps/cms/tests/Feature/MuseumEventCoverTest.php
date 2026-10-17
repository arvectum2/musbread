<?php
namespace Tests\Feature;

use App\Models\MuseumEntry;
use App\Models\MuseumEvent;
use App\Models\MuseumMedia;
use App\Models\MuseumSection;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Storage;
use Illuminate\Validation\ValidationException;
use MoonShine\Laravel\Models\MoonshineUser;
use Tests\TestCase;

class MuseumEventCoverTest extends TestCase
{
    use RefreshDatabase;

    private function entry(string $slug,?int $section=null,string $status='published'):MuseumEntry {
        return MuseumEntry::create([
            'type'=>'news','slug'=>$slug,'title'=>'Материал '.$slug,
            'body'=>'Только тестовые данные','status'=>$status,
            'museum_section_id'=>$section,
        ]);
    }

    private function cover(MuseumEntry $entry):MuseumMedia {
        $image=imagecreatetruecolor(120,80);
        imagefilledrectangle($image,0,0,120,80,imagecolorallocate($image,140,70,40));
        ob_start();
        imagewebp($image,null,80);
        $bytes=ob_get_clean();
        imagedestroy($image);
        $path='museum/media/'.bin2hex(random_bytes(8)).'.webp';
        Storage::disk('local')->put($path,$bytes);
        return MuseumMedia::create([
            'museum_entry_id'=>$entry->id,'storage_path'=>$path,
            'sha256'=>hash('sha256',$bytes),'alt'=>'Коричневая керамическая хлебная форма на белом столе',
            'caption'=>'Проверенная редакторская подпись',
            'long_description'=>'Тестовое подробное описание музейного предмета',
            'mime'=>'image/webp','width'=>120,'height'=>80,'size_bytes'=>strlen($bytes),
        ]);
    }

    private function event(?int $cover,?int $section=null):MuseumEvent {
        return MuseumEvent::create([
            'slug'=>'museum-cover-event','title'=>'QA событие с обложкой',
            'starts_at'=>'2026-12-15','category'=>'Тестовая выставка',
            'body'=>'Тестовая программа','excerpt'=>'Описание тестовой программы',
            'status'=>'published','museum_section_id'=>$section,'cover_media_id'=>$cover,
        ]);
    }

    private function snapshot():array {
        $dir=storage_path('framework/testing/tz147-'.bin2hex(random_bytes(5)));
        mkdir($dir,0700,true);
        try{
            $this->artisan('museum:export',[
                '--output'=>$dir.'/published.json',
                '--manifest'=>$dir.'/manifest.json',
                '--media-output-dir'=>$dir.'/media',
                '--document-output-dir'=>$dir.'/documents',
            ])->assertSuccessful();
            $json=json_decode(file_get_contents($dir.'/published.json'),true,flags:JSON_THROW_ON_ERROR);
            $cover=$json['events'][0]['cover_image']??null;
            if($cover!==null) {
                $this->assertFileExists($dir.$cover['src']);
                $this->assertSame(
                    hash_file('sha256',$dir.$cover['src']),
                    substr(basename($cover['src']),0,64));
            }
            return $json;
        }finally{
            $iterator=new \RecursiveIteratorIterator(
                new \RecursiveDirectoryIterator($dir,\FilesystemIterator::SKIP_DOTS),
                \RecursiveIteratorIterator::CHILD_FIRST);
            foreach($iterator as $file){
                if($file->isDir())rmdir($file->getPathname());
                else unlink($file->getPathname());
            }
            rmdir($dir);
        }
    }

    public function test_approved_cover_exports_image_alt_caption_and_withdraws_with_owner():void {
        Storage::fake('local');
        $owner=$this->entry('cover-owner');
        $media=$this->cover($owner);
        $event=$this->event($media->id);
        $snapshot=$this->snapshot();
        $this->assertSame('/media/'.$media->sha256.'.webp',$snapshot['events'][0]['cover_image']['src']);
        $this->assertSame($media->alt,$snapshot['events'][0]['cover_image']['alt']);
        $this->assertSame($media->caption,$snapshot['events'][0]['cover_image']['caption']);
        $this->assertSame($media->long_description,$snapshot['events'][0]['cover_image']['long_description']);
        $owner->update(['status'=>'draft']);
        $this->assertArrayNotHasKey('cover_image',$this->snapshot()['events'][0]);
        $owner->update(['status'=>'published']);
        $this->assertArrayHasKey('cover_image',$this->snapshot()['events'][0]);
        $media->delete();
        $this->assertNull($event->fresh()->cover_media_id);
        $this->assertArrayNotHasKey('cover_image',$this->snapshot()['events'][0]);
    }

    public function test_rejects_draft_and_other_section_covers_even_from_admin():void {
        Storage::fake('local');
        $section=MuseumSection::create(['slug'=>'event-gallery','title'=>'Галерея','status'=>'published']);
        $foreign=MuseumSection::create(['slug'=>'private-gallery','title'=>'Чужая галерея','status'=>'published']);
        $image=$this->cover($this->entry('foreign-cover',$foreign->id));
        try{
            $this->event($image->id,$section->id);
            $this->fail('Cover from another editorial section accepted');
        }catch(ValidationException $e){$this->assertArrayHasKey('cover_media_id',$e->errors());}
        $draft=$this->cover($this->entry('draft-cover',$section->id,'draft'));
        try{
            $this->event($draft->id,$section->id);
            $this->fail('Draft media leaked through a published event');
        }catch(ValidationException $e){$this->assertArrayHasKey('cover_media_id',$e->errors());}
    }

    public function test_guest_cannot_edit_event_cover_and_form_offers_only_published_media():void {
        Storage::fake('local');
        $image=$this->cover($this->entry('published-photo'));
        $draft=$this->cover($this->entry('secret-draft-photo',null,'draft'));
        $draft->update(['alt'=>'Частный черновой кадр музейной выставки']);
        $uri='/admin/resource/museum-event-resource/museum-event-form-page';
        $this->get($uri)->assertRedirect('/admin/login');
        $this->actingAs(MoonshineUser::factory()->create(),'moonshine')
            ->get($uri)->assertOk()->assertSee('name="cover_media_id"',false)
            ->assertSee($image->alt)->assertDontSee($draft->alt);
    }
}
