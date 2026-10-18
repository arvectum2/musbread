<?php

namespace App\Console\Commands;

use App\Models\MuseumEntry;
use App\Models\MuseumEvent;
use App\Models\MuseumSection;
use Illuminate\Console\Command;
use Illuminate\Support\Facades\DB;
use RuntimeException;
use Throwable;

/**
 * Ten real newest museum news descriptions + exactly one separately evidenced
 * event on 2026-11-03. Source news publication date is not the event date.
 * Never imports unavailable photos or automatic bookings.
 */
final class ImportOfficialNews extends Command
{
    protected $signature='museum:import-official-news
        {--apply : Create ten private source-backed news entries and one dated event draft}
        {--source= : Override source JSON for negative verification tests}';
    protected $description='Source-verified museum news and 3 November event draft, no fake dates/tickets';

    private const INDEX_DIGEST='f19cc32cff03714837bd9cdd62d0fd02fc41a7a4b97d26ec242e4a37e66070af';
    private const SOURCE_SET_DIGEST='0669cb983ce888ef97652c4970c0c087f214005a535caaddccaf9ab5706dc469';
    private const EVENT_SLUG='museum-night-of-arts-2026';
    private const SOURCE_EVENT_SLUG='museum-news-2026-10-16-noch-iskusstv-v-muzee-hleba';

    public function handle():int
    {
        if ($this->option('apply') && app()->environment('production')){
            $this->error('Production bulk news/event imports forbidden. Approve content via editorial CMS.');
            return self::FAILURE;
        }
        try{
            $source=json_decode((string)file_get_contents($this->option('source')
                ?:base_path('../web/src/data/official-museum-news.json')),true,flags:JSON_THROW_ON_ERROR);
            if(($source['source']??null)!=='https://muzei-xleb.ru'
                ||($source['index_url']??null)!=='https://muzei-xleb.ru/novosty'
                ||($source['count']??null)!==10
                || !is_array($source['articles']??null)
                ||count($source['articles'])!==10
                ||($source['index_html_sha256']??null)!==self::INDEX_DIGEST
                ||hash('sha256',$source['index_html']??'')!==self::INDEX_DIGEST){
                throw new RuntimeException('Museum latest news index digest or structure changed');
            }
            $set=[];
            foreach($source['articles'] as $article){
                $set[]=($article['source_url']??'').'|'.($article['html_sha256']??'');
            }
            if(hash('sha256',implode("\n",$set))!==self::SOURCE_SET_DIGEST){
                throw new RuntimeException('Original ten news URL+HTML signatures mismatch');
            }
            $seen=[];$plan=[];
            foreach($source['articles'] as $item){
                $slug=$item['slug']??'';
                $path=$item['path']??'';
                $date=$item['published_on']??'';
                if(!is_string($path)
                    || !preg_match('#^/novosty/(20\d{2}-\d\d-\d\d)/([a-z0-9-]+)$#D',$path,$m)
                    ||$date!==$m[1]
                    ||$slug!=='museum-news-'.$date.'-'.$m[2]
                    ||($item['source_url']??null)!=='https://muzei-xleb.ru'.$path
                    ||isset($seen[$slug])
                    ||($item['photos_rights_confirmed']??null)!==false
                    ||!is_string($item['title']??null)||mb_strlen($item['title'])<8
                    ||!is_string($item['intro']??null)||mb_strlen($item['intro'])<38
                    ||!is_string($item['html']??null)||mb_strlen($item['html'])<80
                    ||($item['html_sha256']??null)!==hash('sha256',$item['html'])){
                    throw new RuntimeException('Museum news signature/metadata verification failed: '.$slug);
                }
                $existing=MuseumEntry::where('slug',$slug)->first();
                if($existing && ($existing->type!=='news' || $existing->museum_section_id!==null)){
                    throw new RuntimeException('Unrelated CMS record already owns news slug: '.$slug);
                }
                $seen[$slug]=true;
                $plan[$slug]=compact('item','existing');
            }
            $first=$plan[self::SOURCE_EVENT_SLUG]['item']??null;
            if (!$first || ($first['title']??'')!=='Ночь искусств в Музее Хлеба'
                || !str_contains($first['html'],'3 ноября 2026 г., 18:00–20:00')
                || !str_contains($first['html'],'Петербург гостеприимный')){
                throw new RuntimeException('Cannot prove 3 November programme date and time from original museum article');
            }
            $section=MuseumSection::where('slug','agenda-events')->first();
            if(!$section ||$section->parent?->slug!=='agenda'){
                throw new RuntimeException('Missing original museum agenda section');
            }
            $event=MuseumEvent::where('slug',self::EVENT_SLUG)->first();
            if($event && ($event->museum_section_id!==$section->id
                ||$event->starts_at?->format('Y-m-d')!=='2026-11-03')){
                throw new RuntimeException('Unrelated CMS event owns night of arts identity');
            }
            foreach($plan as $slug=>$row){
                $this->line(($row['existing']?'KEEP EDITOR':'NEW NEWS DRAFT').' '.$slug);
            }
            $this->line(($event?'KEEP EDITOR':'NEW EVENT DRAFT').' '.self::EVENT_SLUG.' (2026-11-03, 18:00–20:00)');
            if(!$this->option('apply')){
                $this->info('Dry run only: no news, events, images or bookings created.');
                return self::SUCCESS;
            }
            DB::transaction(function () use($plan,$section,$first){
                foreach($plan as $slug=>$row){
                    $i=$row['item'];
                    $url=htmlspecialchars($i['source_url'],ENT_QUOTES|ENT_SUBSTITUTE,'UTF-8');
                    MuseumEntry::firstOrCreate(['slug'=>$slug],[
                        'type'=>'news','museum_section_id'=>null,
                        'title'=>mb_substr($i['title'],0,255),
                        'h1'=>mb_substr($i['title'],0,255),
                        'excerpt'=>$i['intro'],
                        'body'=>$i['html'].'<p><a href="'.$url.'">Первоначальная публикация музея ↗</a></p>',
                        'status'=>'draft','published_at'=>null,
                    ]);
                }
                $url=htmlspecialchars($first['source_url'],ENT_QUOTES|ENT_SUBSTITUTE,'UTF-8');
                MuseumEvent::firstOrCreate(['slug'=>self::EVENT_SLUG],[
                    'museum_section_id'=>$section->id,
                    'title'=>'Ночь искусств в Музее Хлеба',
                    'h1'=>'Ночь искусств в Музее Хлеба',
                    'category'=>'Музейное событие',
                    'starts_at'=>'2026-11-03','ends_at'=>'2026-11-03',
                    'excerpt'=>'Программа «Петербург гостеприимный», 3 ноября 2026 года, 18:00–20:00. Дата и время опубликованы музеем.',
                    'body'=>$first['html'].'<p><a href="'.$url.'">Оригинальная программа музея ↗</a></p>',
                    'status'=>'draft','published_at'=>null,
                ]);
            });
            $this->info('10 unpublished CMS news entries plus one verified museum event (Nov 3 18:00–20:00); zero media or tickets.');
            return self::SUCCESS;
        }catch(Throwable $e){
            $this->error('Official museum news import refused: '.$e->getMessage());
            return self::FAILURE;
        }
    }
}
