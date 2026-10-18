<?php

declare(strict_types=1);

namespace App\Console\Commands;

use App\Models\MuseumEntry;
use App\Models\MuseumSection;
use Illuminate\Console\Command;
use Illuminate\Support\Facades\DB;
use RuntimeException;
use Throwable;

/** Original museum past/virtual exhibits with editorial rights gate. */
final class ImportOfficialExhibitionArchive extends Command
{
    protected $signature='museum:import-official-exhibition-archive
        {--apply : Save original museum exhibition texts as private editable entries}
        {--source= : Override source JSON for tamper/negative tests}';
    protected $description='Source-verified museum historical and virtual exhibition details, private only';
    private const SOURCE='https://muzei-xleb.ru';
    private const SET_SHA='f4c66b2ecb2dc0410e12c1c9e96a83be28857755d53dbea6001f726f420b1e47';
    private const GROUPS=['exhibitions-past'=>12,'exhibitions-virtual'=>12];

    public function handle():int
    {
        if ($this->option('apply') && app()->environment('production')) {
            $this->error('Bulk archive exhibition import forbidden on production.');
            return self::FAILURE;
        }
        try {
            $idx=json_decode((string)file_get_contents(base_path('../web/src/data/official-exhibition-indexes.json')),
                true,flags:JSON_THROW_ON_ERROR);
            $src=json_decode((string)file_get_contents($this->option('source')
                ?:base_path('../web/src/data/official-exhibition-archive.json')),
                true,flags:JSON_THROW_ON_ERROR);
            if(($idx['source']??null)!==self::SOURCE || ($src['source']??null)!==self::SOURCE
                || ($src['expected']??null)!==24 || ($src['count']??null)!==24
                || !is_array($src['exhibitions']??null) || count($src['exhibitions'])!==24
                || ($src['errors']??null)!==[] || !is_array($idx['indexes']??null)) {
                throw new RuntimeException('Original exhibition archival corpus incomplete');
            }
            $groups=[];$sections=[];$links=[];
            foreach($idx['indexes'] as $item){
                $slug=$item['slug']??'';
                if(!array_key_exists($slug,self::GROUPS))continue;
                $section=MuseumSection::where('slug',$slug)->first();
                if(!$section || $section->parent?->slug!=='exhibitions-guide'
                    || ($item['html_sha256']??null)!==hash('sha256',$item['html']??'')
                    || ($src['catalogue_shas'][$slug]??null)!==$item['html_sha256']
                    || count($item['linked_exhibitions']??[])!==self::GROUPS[$slug]){
                    throw new RuntimeException('Cannot verify museum exhibition index '.$slug);
                }
                $groups[$slug]=$item;
                $sections[$slug]=$section;
                foreach($item['linked_exhibitions'] as $link){
                    if(isset($links[$link['source_url']]))throw new RuntimeException('Exhibition link repeated');
                    $links[$link['source_url']]=['index_slug'=>$slug,'index_title'=>$link['title']];
                }
            }
            if(count($groups)!==2 || count($links)!==24)throw new RuntimeException('Lost a source museum archive catalogue');
            $set=[];
            foreach($src['exhibitions'] as $item){
                $set[]=($item['source_url']??'').'|'.($item['html_sha256']??'')
                    .'|'.($item['source_page_sha256']??'')
                    .'|'.implode(',',array_column($item['image_links']??[],'url'));
            }
            if(hash('sha256',implode("\n",$set))!==self::SET_SHA) {
                throw new RuntimeException('Original exhibition text/image-source signatures changed');
            }
            $counts=[];$plan=[];
            foreach($src['exhibitions'] as $item){
                $url=$item['source_url']??'';
                $path=$item['path']??'';
                $category=$item['category_slug']??'';
                $slug=$item['slug']??'';
                if(!preg_match('#^/vistavky/20\d{2}-\d\d-\d\d/[a-z0-9-]+$#D',$path)
                    || $url!==self::SOURCE.$path
                    || ($links[$url]['index_slug']??null)!==$category
                    || ($links[$url]['index_title']??null)!==($item['index_label']??null)
                    || ($src['catalogue_shas'][$category]??null)!==($item['source_index_sha256']??null)
                    || $slug!=='museum-exhibit-'.str_replace('/','-',substr($path,strlen('/vistavky/')))
                    || isset($plan[$slug])
                    || ($item['photos_rights_confirmed']??null)!==false
                    || !is_string($item['title']??null) || mb_strlen($item['title'])<8
                    || !is_string($item['html']??null)
                    || !is_string($item['intro']??null)
                    || ($item['html_sha256']??null)!==hash('sha256',$item['html'])
                    || (($item['image_only']??false)===true
                        ? ($item['html']!=='' || $item['intro']!==''
                            || !preg_match('/^[a-f0-9]{64}$/D',(string)($item['source_page_sha256']??''))
                            || count($item['image_links']??[])<1)
                        : (mb_strlen($item['html'])<12 || mb_strlen($item['intro'])<8))) {
                    throw new RuntimeException('Original museum exhibition detail source mismatch: '.$slug);
                }
                $existing=MuseumEntry::where('slug',$slug)->first();
                if ($existing && ($existing->type!=='exhibition'
                    || $existing->museum_section_id!==$sections[$category]->id)) {
                    throw new RuntimeException('Other museum editor owns exhibition identity: '.$slug);
                }
                $counts[$category]=($counts[$category]??0)+1;
                $plan[$slug]=['item'=>$item,'section'=>$sections[$category],
                    'existing'=>$existing!==null];
                $this->line(($existing?'KEEP EDITOR':'NEW PRIVATE EXHIBITION').' '.$slug);
            }
            if(count($plan)!==24 || ($counts['exhibitions-past']??0)!==12
                || ($counts['exhibitions-virtual']??0)!==12){
                throw new RuntimeException('Museum archival category membership inconsistent');
            }
            if (!$this->option('apply')) {
                $this->info('Dry run only. No museum archived exhibition changed.');
                return self::SUCCESS;
            }
            DB::transaction(function()use($plan):void {
                foreach($plan as $slug=>$row){
                    $i=$row['item'];
                    $url=htmlspecialchars($i['source_url'],ENT_QUOTES|ENT_SUBSTITUTE,'UTF-8');
                    MuseumEntry::firstOrCreate(['slug'=>$slug],[
                        'type'=>'exhibition','museum_section_id'=>$row['section']->id,
                        'title'=>mb_substr($i['title'],0,255),
                        'h1'=>mb_substr($i['title'],0,255),
                        'excerpt'=>$i['intro']?:null,
                        'body'=>$i['html'].'<p><a href="'.$url.'">Оригинальная архивная выставка музея ↗</a></p>',
                        'status'=>'draft','published_at'=>null,
                    ]);
                }
            });
            $this->info('24 real museum exhibition descriptions preserved as private drafts (12 past, 12 virtual).');
            return self::SUCCESS;
        }catch(Throwable $e){
            $this->error('Original museum exhibition archive rejected: '.$e->getMessage());
            return self::FAILURE;
        }
    }
}
