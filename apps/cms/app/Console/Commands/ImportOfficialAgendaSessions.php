<?php

namespace App\Console\Commands;

use App\Models\MuseumEvent;
use App\Models\MuseumSection;
use Illuminate\Console\Command;
use Illuminate\Support\Facades\DB;
use RuntimeException;
use Throwable;

/** Strict migration of 124 individually dated / timed ORIGINAL weekly museum
 * bulletin rows as private event drafts. No guessing duration/availability.
 */
final class ImportOfficialAgendaSessions extends Command
{
    protected $signature='museum:import-official-agenda
        {--apply : Create 124 individually evidenced draft events}
        {--source= : Alternate fixture for tamper tests}';
    protected $description='Import original Sep–Oct 2026 timed sessions as private MoonShine draft events';

    private const SET_DIGEST='221e946c7c0e1c3c8bbe6583aebe446069fcd278d18e0c3f05ad50641a192542';
    private const CATEGORIES=[
        'Экскурсия'=>'agenda-excursions',
        'Мастер-класс'=>'agenda-workshops',
        'Литературная гостиная'=>'agenda-meetings',
        'Интерактивное занятие'=>'agenda-events',
        'Тематическая программа'=>'agenda-events',
    ];
    private const ORIGINAL=[
        'https://muzei-xleb.ru/novosty/2026-10-12/sobytiya-v-muzee-s-12-po-19-oktyabrya',
        'https://muzei-xleb.ru/novosty/2026-10-05/sobytiya-v-muzee-s-5-po-12-oktyabrya',
        'https://muzei-xleb.ru/novosty/2026-09-28/sobytiya-v-muzee-s-28-sentyabrya-po-5-oktyabrya',
        'https://muzei-xleb.ru/novosty/2026-09-21/sobytiya-v-muzee-s-21-po-28-sentyabrya',
        'https://muzei-xleb.ru/novosty/2026-09-14/sobytiya-v-muzee-s-14-po-21-sentyabrya',
        'https://muzei-xleb.ru/novosty/2026-09-07/sobytiya-v-muzee-s-7-po-14-sentyabrya',
    ];

    public function handle():int
    {
        if($this->option('apply') && app()->environment('production')){
            $this->error('Mass import forbidden in production. Editors must approve each museum session.');
            return self::FAILURE;
        }
        try{
            $source=json_decode((string)file_get_contents($this->option('source')
                ?:base_path('../web/src/data/official-agenda-sessions.json')),true,flags:JSON_THROW_ON_ERROR);
            if(($source['source']??null)!=='https://muzei-xleb.ru'
                ||($source['original_bulletin_count']??null)!==6
                ||($source['raw_rows']??null)!==140
                ||($source['unique_sessions']??null)!==124
                ||!is_array($source['sessions']??null)
                ||count($source['sessions'])!==124){
                throw new RuntimeException('Original weekly museum programme count/source changed');
            }
            $sections=[];
            foreach(array_unique(array_values(self::CATEGORIES)) as $slug){
                $section=MuseumSection::where('slug',$slug)->first();
                if(!$section || $section->parent?->slug!=='agenda'){
                    throw new RuntimeException('Invalid editorial destination for event: '.$slug);
                }
                $sections[$slug]=$section;
            }
            $set=[];$rows=[];$seen=[];
            foreach($source['sessions'] as $entry){
                $slug=$entry['slug']??'';
                $day=$entry['date']??'';
                $time=$entry['time']??'';
                $title=$entry['title']??'';
                $category=$entry['category']??'';
                $urls=$entry['source_urls']??[];
                $digests=$entry['source_html_sha256']??[];
                $age=$entry['age_min']??null;
                $sourceRows=$entry['source_rows']??[];
                if(!is_string($slug)||!is_string($day)||!is_string($time)
                    ||!is_string($title)||!is_string($category)
                    || !preg_match('/^2026-(09|10)-\d\d$/D',$day)
                    || !preg_match('/^\d\d:\d\d$/D',$time)
                    || !preg_match('/^museum-session-2026-(09|10)-\d\d-\d{4}-[0-9a-f]{12}$/D',$slug)
                    || !str_starts_with($slug,'museum-session-'.$day.'-'.str_replace(':','',$time).'-')
                    || !isset(self::CATEGORIES[$category])
                    || !is_array($urls)||count($urls)<1||count($urls)>2
                    || count($digests)!==count($urls)
                    || !is_array($sourceRows)||count($sourceRows)!==count($urls)
                    || !is_int($age) ||$age<5 ||$age>18
                    || !str_contains($title,'«') && !str_contains($title,'“')
                    || !is_string($entry['original_row']??null)
                    || !str_starts_with($entry['original_row'],$time.' '.$title)
                    || isset($seen[$slug])){
                    throw new RuntimeException('Official individual session metadata invalid: '.$slug);
                }
                foreach($urls as $k=>$url){
                    if(!in_array($url,self::ORIGINAL,true)
                        ||!preg_match('/^[a-f0-9]{64}$/D',(string)($digests[$k]??''))
                        || !is_string($sourceRows[$k])
                        || !str_starts_with($sourceRows[$k],$time.' ')){
                        throw new RuntimeException('Unverified original museum bulletin link');
                    }
                }
                $set[]=$slug.'|'.$day.'|'.$time.'|'.$title.'|'.$category.'|'.$urls[0].'|'.$digests[0];
                $existing=MuseumEvent::where('slug',$slug)->first();
                $expectedSection=$sections[self::CATEGORIES[$category]];
                if($existing && ($existing->museum_section_id!==$expectedSection->id
                    ||$existing->starts_at?->format('Y-m-d')!==$day)){
                    throw new RuntimeException('Session slug is owned by different CMS event '.$slug);
                }
                $seen[$slug]=true;
                $rows[]=compact('entry','expectedSection','existing');
            }
            if(hash('sha256',implode("\n",$set))!==self::SET_DIGEST){
                throw new RuntimeException('124 original event row signatures altered/reordered');
            }
            $new=count(array_filter($rows,fn($row)=>!$row['existing']));
            $this->info("Validated 124 unique dated/timed museum sessions from 140 original rows; {$new} new drafts; no photos or inferred durations.");
            if(!$this->option('apply')){
                $this->info('Dry run: no museum events changed.');
                return self::SUCCESS;
            }
            DB::transaction(function () use($rows){
                foreach($rows as $row){
                    $s=$row['entry'];
                    $source=htmlspecialchars($s['source_urls'][0],ENT_QUOTES|ENT_SUBSTITUTE,'UTF-8');
                    $when=htmlspecialchars($s['date'].' '.$s['time'],ENT_QUOTES|ENT_SUBSTITUTE,'UTF-8');
                    $title=htmlspecialchars($s['title'],ENT_QUOTES|ENT_SUBSTITUTE,'UTF-8');
                    MuseumEvent::firstOrCreate(['slug'=>$s['slug']],[
                        'title'=>$s['title'],'h1'=>$s['title'],'category'=>$s['category'],
                        'starts_at'=>$s['date'],'ends_at'=>$s['date'],
                        'museum_section_id'=>$row['expectedSection']->id,
                        'excerpt'=>'Музейная афиша: '.$s['date'].' в '.$s['time'].'; '.$s['age_min'].'+. Время начала и возраст из оригинала.',
                        'body'=>'<p><strong>'.$when.'</strong>: '.$title.' ('.$s['age_min'].'+).</p>'
                            .'<p>Оригинальная музейная программа: <a href="'.$source.'">афиша на действующем сайте музея</a>. '
                            .'Продолжительность, билеты и наличие мест не подтверждены.</p>',
                        'status'=>'draft','published_at'=>null,
                    ]);
                }
            });
            $this->info('Saved private MoonShine drafts only. Re-running preserves human editorial changes.');
            return self::SUCCESS;
        }catch(Throwable $e){
            $this->error('Museum agenda import refused: '.$e->getMessage());
            return self::FAILURE;
        }
    }
}
