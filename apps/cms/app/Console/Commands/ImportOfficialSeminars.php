<?php

namespace App\Console\Commands;

use App\Models\MuseumEntry;
use App\Models\MuseumSection;
use Illuminate\Console\Command;
use Illuminate\Support\Facades\DB;
use RuntimeException;
use Throwable;

/** Seven original signed museum seminar detail pages as nonpublic editable CMS
 * articles. The source VK recordings themselves are not rehosted.
 */
final class ImportOfficialSeminars extends Command
{
    protected $signature='museum:import-official-seminars
        {--apply : Save 7 original dated seminar articles as private CMS drafts}
        {--source= : Alternative path for negative verification tests}';
    protected $description='Seven genuine dated museum seminars, no fabricated conferences or rights';

    private const INDEX_SHA='d3317f19b3b1a78b1b8478e73205e74b57d8fafe6f2939cf13540a483cb6158e';
    private const ROW_SET_SHA='75cb7c1be499edc9b89ad8c2ae59ad53ebe150a37ad2b7cfef4706b95f248d1f';

    public function handle():int
    {
        if($this->option('apply') && app()->environment('production')){
            $this->error('Bulk source imports are disabled in production; use the editorial workflow.');
            return self::FAILURE;
        }
        try{
            $path=$this->option('source') ?: base_path('../web/src/data/official-museum-seminars.json');
            $source=json_decode((string)file_get_contents($path),true,flags:JSON_THROW_ON_ERROR);
            if(($source['source']??'')!=='https://muzei-xleb.ru'
                ||($source['index_url']??'')!=='https://muzei-xleb.ru/seminary'
                ||($source['index_html_sha256']??'')!==self::INDEX_SHA
                ||($source['count']??null)!==7
                ||($source['video_count']??null)!==16
                || !is_array($source['seminars']??null)
                || count($source['seminars'])!==7){
                throw new RuntimeException('Original seven museum seminar index metadata changed');
            }
            $section=MuseumSection::where('slug','science-conferences')->first();
            if(!$section || $section->parent?->slug!=='science'){
                throw new RuntimeException('Original science-conferences section missing');
            }
            $seen=[];$items=[];$lines=[];
            foreach($source['seminars'] as $item){
                $slug=$item['id']??'';
                $title=$item['title']??'';
                $date=$item['date_start']??'';
                $end=$item['date_end']??null;
                $url=$item['source_url']??'';
                $sha=$item['page_html_sha256']??'';
                $videos=$item['videos']??null;
                if(!is_string($slug)
                    ||!preg_match('/^science-seminar-20\d\d-\d\d-\d\d-\d{2,4}$/D',$slug)
                    ||isset($seen[$slug])
                    ||!is_string($title)||mb_strlen($title)<20
                    ||!is_string($date)||!preg_match('/^20(20|21|22|23|24|25|26)-\d\d-\d\d$/D',$date)
                    ||!str_contains($slug,'science-seminar-'.$date.'-')
                    ||($end!==null&&!is_string($end))
                    ||($end!==null&&strcmp($end,$date)<0)
                    ||!is_string($url)||!str_starts_with($url,'https://muzei-xleb.ru/seminar-')
                    ||!preg_match('/^[a-f0-9]{64}$/D',$sha)
                    ||!is_array($videos)||count($videos)!==($item['video_count']??-1)
                    || !in_array(count($videos),[2,3],true)
                    ||($item['media_rehosted']??true)!==false
                    ||($item['photo_rights_confirmed']??true)!==false){
                    throw new RuntimeException('Original seminar entry invalid '.$slug);
                }
                foreach($videos as $v){
                    $embed=$v['embed_url']??'';
                    $parts=parse_url($embed);
                    if(!$parts||($parts['scheme']??'')!=='https'
                       ||!in_array($parts['host']??'', ['vk.com','vkvideo.ru'],true)
                       ||($parts['path']??'')!=='/video_ext.php'
                       ||str_contains($embed,'autoplay=')){
                        throw new RuntimeException('Unsafe seminar video source '.$slug);
                    }
                }
                $existing=MuseumEntry::where('slug',$slug)->first();
                if($existing &&($existing->type!=='page'
                    ||$existing->museum_section_id!==$section->id)){
                    throw new RuntimeException('Seminar slug belongs to unrelated CMS article '.$slug);
                }
                $seen[$slug]=true;
                $items[]=compact('item','existing');
                $lines[]=implode('|',[$slug,$title,$date,$end??'',$url,$sha,(string)count($videos)]);
            }
            if(hash('sha256',implode("\n",$lines))!==self::ROW_SET_SHA){
                throw new RuntimeException('Museum seminar titles/dates/original page hashes changed');
            }
            $new=count(array_filter($items,static fn($row)=>!$row['existing']));
            $this->info("Verified 7 real original museum seminars with 16 original VK videos; {$new} new drafts.");
            if(!$this->option('apply')){
                $this->info('Dry run, no entries created.');
                return self::SUCCESS;
            }
            DB::transaction(function() use($items,$section){
                foreach($items as $row){
                    $i=$row['item'];
                    $link=htmlspecialchars($i['source_url'],ENT_QUOTES|ENT_SUBSTITUTE,'UTF-8');
                    $date=htmlspecialchars($i['date_start'],ENT_QUOTES,'UTF-8');
                    $title=htmlspecialchars($i['title'],ENT_QUOTES|ENT_SUBSTITUTE,'UTF-8');
                    MuseumEntry::firstOrCreate(['slug'=>$i['id']],[
                        'type'=>'page',
                        'museum_section_id'=>$section->id,
                        'title'=>$i['title'],
                        'h1'=>$i['title'],
                        'excerpt'=>'Реальный научный семинар музея от '.$date.'.'
                            .' В официальном источнике опубликовано '.$i['video_count'].' видеозаписи/части.',
                        'body'=>'<p>Состоявшийся семинар <strong>'.$date.'</strong>: '.$title.'</p>'
                            .'<p><a href="'.$link.'">Оригинальная научная страница музея ↗</a></p>'
                            .'<p>Записи доступны по источнику; отдельные права и субтитры требуют подтверждения.</p>',
                        'status'=>'draft','published_at'=>null,
                    ]);
                }
            });
            $this->info('Only private draft CMS entries created. Approved editor versions will not be overwritten.');
            return self::SUCCESS;
        }catch(Throwable $e){
            $this->error('Museum seminar import refused: '.$e->getMessage());
            return self::FAILURE;
        }
    }
}
