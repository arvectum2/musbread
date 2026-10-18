<?php

namespace App\Console\Commands;

use App\Models\MuseumEntry;
use App\Models\MuseumSection;
use Illuminate\Console\Command;
use Illuminate\Support\Facades\DB;
use RuntimeException;
use Throwable;

/**
 * Existing museum exhibition source edition (four indexes + six complete
 * current/traveling exhibition texts). No virtual exhibition fabricated.
 * No photos, rights claims, speculative start/end dates or ticket availability.
 */
final class ImportOfficialExhibitions extends Command
{
    protected $signature='museum:import-official-exhibitions
        {--apply : Create four category drafts and six original full exhibition drafts}
        {--source= : Override verified exhibition detail fixture to test failure handling}';
    protected $description='Import verified museum exhibition text into existing MoonShine CMS as private editorial drafts';

    private const INDEX_SHA=[
        'exhibitions-current'=>'e25db8fc56df9eab0f8b29596aa9689c9608709a244e408725b6a0f3e6fd7b88',
        'exhibitions-traveling'=>'4ce6fc2e506812a34ef28a9c85fb35735af6cb7ac9867fb8b8f3a63ec4c56186',
        'exhibitions-past'=>'2b073a64459456fb10dabc5e0e78ce5ba61292ce55dc2956117601e428998e01',
        'exhibitions-virtual'=>'d3390b182091829774cb8ce0b984973841075a183c39839bdb50d253104e885f',
    ];
    private const COUNTS=[
        'exhibitions-current'=>2,
        'exhibitions-traveling'=>4,
        'exhibitions-past'=>12,
        'exhibitions-virtual'=>12,
    ];
    private const SOURCE_SET_SHA='ef33fa224557e4adebc61d916019d0e2a1323db59ca7ce4a86d2de56edc980bc';

    public function handle():int
    {
        if ($this->option('apply') && app()->environment('production')){
            $this->error('Production bulk source import forbidden; museum editor must individually approve.');
            return self::FAILURE;
        }
        try {
            $idx=json_decode((string) file_get_contents(base_path('../web/src/data/official-exhibition-indexes.json')),
                true,flags:JSON_THROW_ON_ERROR);
            $src=json_decode((string) file_get_contents($this->option('source')
                ?:base_path('../web/src/data/official-exhibition-details.json')),
                true,flags:JSON_THROW_ON_ERROR);
            if (($idx['source']??null)!=='https://muzei-xleb.ru'
                || ($src['source']??null)!=='https://muzei-xleb.ru'
                || ($idx['count']??null)!==4 || !is_array($idx['indexes']??null)
                || count($idx['indexes'])!==4 || ($src['count']??null)!==6
                || !is_array($src['exhibitions']??null)||count($src['exhibitions'])!==6){
                throw new RuntimeException('Museum exhibition source registry structure mismatch');
            }
            $pages=[];$entries=[];$seen=[];
            foreach($idx['indexes'] as $index){
                $slug=$index['slug']??'';
                $hash=self::INDEX_SHA[$slug]??null;
                $section=MuseumSection::where('slug',$slug)->first();
                $expected='/vistavky/'.match($slug){
                    'exhibitions-current'=>'tekushchie-vystavki',
                    'exhibitions-traveling'=>'vyezdnye-vystavki',
                    'exhibitions-past'=>'proshedshie-vystavki',
                    'exhibitions-virtual'=>'virtualnye-vystavki',
                    default=>throw new RuntimeException('Unexpected category slug'),
                };
                if (!$hash || isset($seen[$slug]) || ($index['html_sha256']??null)!==$hash
                    || hash('sha256',$index['html']??'')!==$hash
                    || ($index['source_url']??null)!=='https://muzei-xleb.ru'.$expected
                    || ($index['path']??null)!==$expected
                    || !is_array($index['linked_exhibitions']??null)
                    || count($index['linked_exhibitions'])!==self::COUNTS[$slug]
                    || ($index['images_rights_confirmed']??null)!==false
                    || !$section || $section->parent?->slug!=='exhibitions-guide'
                    || $section->legacy_path!==$expected){
                    throw new RuntimeException('Museum exhibition category signature/navigation changed '.$slug);
                }
                $seen[$slug]=true;
                $existing=MuseumEntry::where('slug',$slug)->first();
                if ($existing && ($existing->type!=='page'||$existing->museum_section_id!==$section->id)){
                    throw new RuntimeException('Unrelated editor owns exhibition category slug');
                }
                $pages[$slug]=compact('index','section','existing');
            }
            $set=[];
            foreach($src['exhibitions'] as $e){
                $set[]=($e['source_url']??'').'|'.($e['html_sha256']??'');
            }
            if(hash('sha256',implode("\n",$set))!==self::SOURCE_SET_SHA){
                throw new RuntimeException('Original six museum exhibition URLs and HTML signatures changed');
            }
            $counts=[];
            foreach($src['exhibitions'] as $e){
                $slug=$e['slug']??'';
                $category=$e['category_slug']??'';
                $path=$e['path']??'';
                $url=$e['source_url']??'';
                $page=$pages[$category]??null;
                if (!in_array($category,['exhibitions-current','exhibitions-traveling'],true)
                    || !preg_match('#^/vistavky/\d{4}-\d\d-\d\d/[a-z0-9-]+$#D',$path)
                    || $url!=='https://muzei-xleb.ru'.$path
                    || $slug!=='museum-exhibit-'.str_replace('/','-',substr($path,strlen('/vistavky/')))
                    || isset($seen[$slug])
                    || !is_array($page)
                    || !in_array($url,array_column($page['index']['linked_exhibitions'],'source_url'),true)
                    || !is_string($e['html']??null)
                    || mb_strlen($e['html'])<100
                    || ($e['html_sha256']??null)!==hash('sha256',$e['html'])
                    || ($e['photos_rights_confirmed']??null)!==false
                    || !is_string($e['title']??null) || mb_strlen($e['title'])<10
                    || !is_string($e['intro']??null) || mb_strlen($e['intro'])<40){
                    throw new RuntimeException('Museum exhibition source not verified: '.$slug);
                }
                $existing=MuseumEntry::where('slug',$slug)->first();
                if($existing && ($existing->type!=='exhibition'
                    ||$existing->museum_section_id!==$page['section']->id)){
                    throw new RuntimeException('An unrelated editor owns exhibition slug '.$slug);
                }
                $seen[$slug]=true;
                $counts[$category]=($counts[$category]??0)+1;
                $entries[$slug]=compact('e','page','existing');
            }
            if(($counts['exhibitions-current']??0)!==2||($counts['exhibitions-traveling']??0)!==4){
                throw new RuntimeException('Expected exactly two current + four traveling exhibition details');
            }
            foreach($pages as $slug=>$row){
                $this->line(($row['existing']?'KEEP EDITOR':'NEW PRIVATE INDEX').' '.$slug);
            }
            foreach($entries as $slug=>$row){
                $this->line(($row['existing']?'KEEP EDITOR':'NEW PRIVATE EXHIBITION').' '.$slug);
            }
            if(!$this->option('apply')){
                $this->info('Dry-run only. No museum publications, no photos, no future exhibitions created.');
                return self::SUCCESS;
            }
            DB::transaction(function()use($pages,$entries){
                foreach($pages as $slug=>$row){
                    $idx=$row['index'];
                    MuseumEntry::firstOrCreate(['slug'=>$slug],[
                        'type'=>'page','museum_section_id'=>$row['section']->id,
                        'title'=>$idx['title'],'h1'=>$idx['title'],
                        'excerpt'=>'Исходная редакция: '.$idx['source_url']
                            .'; снимок от '.substr($idx['captured_utc'],0,10),
                        'body'=>$idx['html'],
                        'status'=>'draft','published_at'=>null,
                    ]);
                }
                foreach($entries as $slug=>$row){
                    $e=$row['e'];
                    $url=htmlspecialchars($e['source_url'],ENT_QUOTES|ENT_SUBSTITUTE,'UTF-8');
                    MuseumEntry::firstOrCreate(['slug'=>$slug],[
                        'type'=>'exhibition','museum_section_id'=>$row['page']['section']->id,
                        'title'=>mb_substr($e['title'],0,255),
                        'h1'=>mb_substr($e['title'],0,255),
                        'excerpt'=>$e['intro'],
                        'body'=>$e['html'].'<p><a href="'.$url.'">'
                            .'Действующая музейная редакция выставки</a></p>',
                        'status'=>'draft','published_at'=>null,
                    ]);
                }
            });
            $this->info('Four category pages and six genuine exhibitions are private MoonShine drafts.');
            return self::SUCCESS;
        }catch(Throwable $e){
            $this->error('Exhibition import refused: '.$e->getMessage());
            return self::FAILURE;
        }
    }
}
