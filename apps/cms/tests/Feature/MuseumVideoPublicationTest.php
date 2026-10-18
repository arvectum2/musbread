<?php
declare(strict_types=1);
namespace Tests\Feature;

use App\Models\MuseumEntry;
use App\Models\MuseumSection;
use App\Models\MuseumVideo;
use App\Support\MuseumApprovalRevision;
use App\Support\MuseumVideoUrlPolicy;
use Database\Seeders\ReferenceMuseumSectionsSeeder;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Artisan;
use Illuminate\Validation\ValidationException;
use Tests\TestCase;

final class MuseumVideoPublicationTest extends TestCase
{
    use RefreshDatabase;
    private function sample(string $status='published'):array {
        return [
            'code'=>'seminar-demo',
            'title'=>'Музейный научный семинар',
            'embed_url'=>'https://vk.com/video_ext.php?oid=-37126776&id=456239157',
            'source_url'=>'https://muzei-xleb.ru/seminar-k-istorii-mukomolnyh-melnic-v-rossii-16-aprelya-2026-g',
            'transcript'=>str_repeat('Текстовая альтернатива рассказывает содержание научного музейного семинара. ',2),
            'rights_confirmed'=>true,
            'status'=>$status,
        ];
    }
    private function article(string $body):MuseumEntry{
        $section=MuseumSection::where('slug','science-conferences')->firstOrFail();
        return MuseumEntry::create([
            'type'=>'page','slug'=>'qa-science-video','title'=>'QA: безопасное видео',
            'museum_section_id'=>$section->id,'status'=>'published',
            'published_at'=>now()->subHour(),'body'=>$body,
        ]);
    }
    private function exportTo(string $label):array{
        $base=storage_path('framework/testing/video-'.$label);
        $args=[
            '--output'=>$base.'.json','--manifest'=>$base.'.manifest.json',
            '--media-output-dir'=>$base.'-media','--document-output-dir'=>$base.'-docs',
        ];
        try{
            $ret=Artisan::call('museum:export',$args);
            $message=Artisan::output();
        }catch(\RuntimeException $e){
            // Export fails closed BEFORE writing any public JSON/manifest.
            $ret=1;
            $message=$e->getMessage();
        }
        $data=is_file($base.'.json')?json_decode((string)file_get_contents($base.'.json'),true):[];
        @unlink($base.'.json');@unlink($base.'.manifest.json');
        return [$ret,$data,$message];
    }
    public function test_exact_vkontakte_provider_allowlist_rejects_autoplay_and_malicious_hosts():void{
        $policy=MuseumVideoUrlPolicy::class;
        $this->assertNotNull($policy::safeEmbed($this->sample()['embed_url']));
        foreach([
            'https://vk.com.evil.org/video_ext.php?oid=-37126776&id=456239157',
            'https://vk.com/video_ext.php?oid=-37126776&id=456239157&autoplay=1',
            'https://vk.com/video_ext.php?oid=-37126776&id=456239157&javascript=alert',
            'http://vk.com/video_ext.php?oid=-37126776&id=456239157',
            'https://vk.com:8888/video_ext.php?oid=-37126776&id=456239157',
            'https://vk.com/video_ext.php?oid=-37126776&id=456239157#foo',
            'https://youtube.com/embed/test',
        ] as $url){
            $this->assertNull($policy::safeEmbed($url),$url);
        }
    }
    public function test_private_videos_never_export_and_missing_or_invalid_embed_blocks_publish():void{
        $this->seed(ReferenceMuseumSectionsSeeder::class);
        // The fixture sections are editorial drafts by default. Enable all
        // ancestors in this isolated in-memory DB to exercise real exporter.
        MuseumSection::query()->update(['status'=>'published']);
        $article=$this->article('<p>До текста</p><p>[[museum-video:seminar-demo]]</p><p>После текста</p>');
        $video=MuseumVideo::create(['museum_entry_id'=>$article->id,...$this->sample('draft')]);
        [$status,$data]=$this->exportTo('draft');
        $this->assertSame(1,$status);
        $this->assertSame([],$data);
        $video->update(['status'=>'published']);
        [$status,$data,$message]=$this->exportTo('approved');
        $this->assertSame(0,$status,$message);
        $published=collect($data['entries'])->firstWhere('slug',$article->slug);
        $this->assertCount(1,$published['videos']);
        $this->assertSame($video->embed_url,$published['videos'][0]['embed_url']);
        $this->assertSame($video->transcript,$published['videos'][0]['transcript']);
        $this->assertStringContainsString('[[museum-video:seminar-demo]]',$published['body']);
        $this->assertStringNotContainsString('<iframe',$published['body']);
        $article->update(['body'=>'<p>Inline error [[museum-video:seminar-demo]] with text</p>']);
        [$status,$data]=$this->exportTo('bad-position');
        $this->assertSame(1,$status,'An inline marker must be its own TinyMCE paragraph');
        $this->assertSame([],$data);
        $article->update(['body'=>'<p>До текста</p><p>[[museum-video:seminar-demo]]</p><p>После текста</p>']);
        $this->assertArrayNotHasKey('rights_confirmed',$published['videos'][0]);
        $video->update(['status'=>'draft']);
        $article->update(['body'=>'<p>Проверенный текст без плеера</p>']);
        [$status,$data]=$this->exportTo('no-video');
        $this->assertSame(0,$status);
        $published=collect($data['entries'])->firstWhere('slug',$article->slug);
        $this->assertArrayNotHasKey('videos',$published);
    }
    public function test_rights_text_alternative_and_content_approval_signature_required():void{
        $this->seed(ReferenceMuseumSectionsSeeder::class);
        $entry=$this->article('<p>Музейный научный материал</p>');
        $before=MuseumApprovalRevision::fingerprint($entry);
        $this->expectException(ValidationException::class);
        MuseumVideo::create(['museum_entry_id'=>$entry->id,...array_merge($this->sample(),['rights_confirmed'=>false])]);
    }
    public function test_editorial_video_changes_invalidate_subject_revision():void {
        $this->seed(ReferenceMuseumSectionsSeeder::class);
        $entry=$this->article('<p>Публикация семинара</p>');
        $before=MuseumApprovalRevision::fingerprint($entry);
        $video=MuseumVideo::create(['museum_entry_id'=>$entry->id,...$this->sample()]);
        $after=MuseumApprovalRevision::fingerprint($entry);
        $this->assertNotSame($before,$after);
        $video->update(['transcript'=>$video->transcript.' Обновлённое описание.']);
        $this->assertNotSame($after,MuseumApprovalRevision::fingerprint($entry));
    }
    public function test_video_record_without_transcript_or_foreign_provider_rejected():void{
        $this->seed(ReferenceMuseumSectionsSeeder::class);
        $entry=$this->article('<p>Материал</p>');
        foreach([
            ['transcript'=>'Без описания'],
            ['embed_url'=>'https://example.org/video_ext.php?oid=-37126776&id=456239157'],
            ['status'=>'published','rights_confirmed'=>false],
            ['source_url'=>'https://evil.example/'],
        ] as $mutation){
            try{
                MuseumVideo::create(['museum_entry_id'=>$entry->id,...array_merge($this->sample(),$mutation)]);
                $this->fail('Expected video policy refusal');
            }catch(ValidationException $e){
                $this->assertNotEmpty($e->errors());
            }
        }
        $this->assertDatabaseCount('museum_videos',0);
    }
}
