<?php

declare(strict_types=1);
namespace App\Console\Commands;

use App\Models\MuseumEntry;
use App\Models\MuseumSection;
use Illuminate\Console\Command;
use Illuminate\Support\Facades\DB;
use RuntimeException;
use Throwable;

/** Four extra REAL past exhibitions linked from source-verified original news. */
final class ImportOfficialNewsLinkedExhibitions extends Command
{
    protected $signature='museum:import-official-news-linked-exhibitions
        {--apply : Save genuinely linked original exhibition texts privately}
        {--source= : Override source JSON for source-validation tests}';
    protected $description='Source-verified exhibitions discovered via the museum historical news archive';
    private const SOURCE='https://muzei-xleb.ru';
    private const SOURCE_SET_DIGEST='6ee09e97ef1702c43dda28c55d5b0588f79c315ad7bf07ddb653a46d78a2d97e';

    public function handle():int
    {
        if($this->option('apply') && app()->environment('production')) {
            $this->error('No bulk source imports in production.');
            return self::FAILURE;
        }
        try {
            $src=json_decode((string)file_get_contents($this->option('source')
                ?:base_path('../web/src/data/official-exhibition-news-linked.json')),
                true,flags:JSON_THROW_ON_ERROR);
            $news=json_decode((string)file_get_contents(
                base_path('../web/src/data/official-museum-news-archive.json')),
                true,flags:JSON_THROW_ON_ERROR);
            if(($src['source']??null)!==self::SOURCE || ($src['count']??null)!==4
                || count($src['exhibitions']??[])!==4 || ($news['source']??null)!==self::SOURCE) {
                throw new RuntimeException('Incomplete four original museum exhibition pages');
            }
            $set=array_map(static fn(array $item):string=>($item['source_url']??'').'|'
                .($item['html_sha256']??'').'|'.($item['linked_news_html_sha256']??''),
                $src['exhibitions']);
            if(hash('sha256',implode("\n",$set))!==self::SOURCE_SET_DIGEST) {
                throw new RuntimeException('Source-verified museum exhibition corpus altered');
            }
            $section=MuseumSection::where('slug','exhibitions-past')->first();
            if(!$section || $section->parent?->slug!=='exhibitions-guide') {
                throw new RuntimeException('Original museum archived exhibition section missing');
            }
            $byNews=[];
            foreach($news['articles']??[] as $entry)$byNews[$entry['slug']]=$entry;
            $plan=[];
            foreach($src['exhibitions'] as $item){
                $path=$item['path']??'';
                $slug=$item['slug']??'';
                $linking=$byNews[$item['linked_news_slug']??'']??null;
                if(!preg_match('#^/vistavky/20\d{2}-\d\d-\d\d/[a-z0-9-]+$#D',$path)
                    || ($item['source_url']??null)!==self::SOURCE.$path
                    || $slug!=='museum-exhibit-'.str_replace('/','-',substr($path,strlen('/vistavky/')))
                    || ($item['category_slug']??null)!=='exhibitions-past'
                    || !is_string($item['title']??null) || mb_strlen($item['title'])<8
                    || !is_string($item['html']??null) || mb_strlen($item['html'])<200
                    || ($item['html_sha256']??null)!==hash('sha256',$item['html'])
                    || !preg_match('/^[a-f0-9]{64}$/D',(string)($item['source_page_sha256']??''))
                    || str_contains(strtolower($item['html']),'<img')
                    || str_contains(strtolower($item['html']),'<script')
                    || ($item['photos_rights_confirmed']??null)!==false
                    || !$linking
                    || ($linking['source_url']??null)!==($item['linked_news_url']??null)
                    || ($linking['html_sha256']??null)!==($item['linked_news_html_sha256']??null)
                    || ($linking['html_sha256']??null)!==hash('sha256',$linking['html'])
                    || !(str_contains($linking['html'],self::SOURCE.$path)
                        || str_contains($linking['html'],'http://muzei-xleb.ru'.$path))
                    || isset($plan[$slug])) {
                    throw new RuntimeException('Source news does not verify museum exhibition '.$slug);
                }
                $existing=MuseumEntry::where('slug',$slug)->first();
                if($existing && ($existing->type!=='exhibition'
                    || $existing->museum_section_id!==$section->id)) {
                    throw new RuntimeException('Other museum content already owns exhibition slug '.$slug);
                }
                $plan[$slug]=$item;
                $this->line(($existing?'KEEP ORIGINAL EDITOR':'NEW SOURCE-VERIFIED DRAFT').' '.$slug);
            }
            if(count($plan)!==4)throw new RuntimeException('Museum original four exhibitions incomplete');
            if(!$this->option('apply')){
                $this->info('Dry run successful, no records edited.');
                return self::SUCCESS;
            }
            DB::transaction(function()use($plan,$section):void{
                foreach($plan as $slug=>$item){
                    $url=htmlspecialchars($item['source_url'],ENT_QUOTES|ENT_SUBSTITUTE,'UTF-8');
                    MuseumEntry::firstOrCreate(['slug'=>$slug],[
                        'type'=>'exhibition','museum_section_id'=>$section->id,
                        'title'=>mb_substr($item['title'],0,255),
                        'h1'=>mb_substr($item['title'],0,255),
                        'excerpt'=>$item['intro']?:null,
                        'body'=>$item['html'].'<p><a href="'.$url.'">Оригинальная музейная выставка ↗</a></p>',
                        'status'=>'draft','published_at'=>null,
                    ]);
                }
            });
            $this->info('4 genuine past museum exhibition texts imported as private drafts.');
            return self::SUCCESS;
        }catch(Throwable $e){
            $this->error('Museum exhibitions source rejected: '.$e->getMessage());
            return self::FAILURE;
        }
    }
}
