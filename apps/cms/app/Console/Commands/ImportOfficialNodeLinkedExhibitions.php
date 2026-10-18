<?php

declare(strict_types=1);
namespace App\Console\Commands;
use App\Models\MuseumEntry;
use App\Models\MuseumSection;
use Illuminate\Console\Command;
use Illuminate\Support\Facades\DB;
use RuntimeException;
use Throwable;

/** Actual original exhibition descriptions resolved from old Drupal /node/N hyperlinks in museum news. */
final class ImportOfficialNodeLinkedExhibitions extends Command
{
    protected $signature='museum:import-official-node-linked-exhibitions
        {--apply : Import genuine old Drupal exhibition descriptions as private drafts}
        {--source= : Read source-verification corpus from an alternate JSON}';
    protected $description='Import exact museum exhibition pages linked by historical Drupal nodes';
    private const SOURCE='https://muzei-xleb.ru';
    private const SOURCE_SET_DIGEST='45a8d90de1028765ae94ceb9d433146e61dc79d690c933d816dfd7690079fc48';
    private const EXPECTED_ITEMS=42;
    private const EXPECTED_NODES=61;

    public function handle():int
    {
        if($this->option('apply') && app()->environment('production')) {
            $this->error('No bulk original-source imports in production.');return self::FAILURE;
        }
        try {
            $src=json_decode((string)file_get_contents((string)($this->option('source')
                ?:base_path('../web/src/data/official-node-linked-exhibitions.json'))),true,flags:JSON_THROW_ON_ERROR);
            $news=json_decode((string)file_get_contents(base_path('../web/src/data/official-museum-news-archive.json')),true,flags:JSON_THROW_ON_ERROR);
            if(($src['source']??null)!==self::SOURCE
                || ($src['node_count']??null)!==self::EXPECTED_NODES
                || ($src['new_exhibition_count']??null)!==self::EXPECTED_ITEMS
                || count($src['exhibitions']??[])!==self::EXPECTED_ITEMS
                || ($news['source']??null)!==self::SOURCE || ($news['count']??null)!==270) {
                throw new RuntimeException('Original linked exhibition corpus absent, incomplete or changed');
            }
            $signed=array_map(static fn(array $a):string=>($a['source_url']??'').'|'.($a['html_sha256']??'')
                 .'|'.($a['source_page_sha256']??'').'|'.($a['node_path']??''),$src['exhibitions']);
            if(hash('sha256',implode("\n",$signed))!==self::SOURCE_SET_DIGEST) {
                throw new RuntimeException('Source-verified museum linked exhibition signatures mismatch');
            }
            $section=MuseumSection::where('slug','exhibitions-past')->first();
            if(!$section || $section->parent?->slug!=='exhibitions-guide'){
                throw new RuntimeException('Original past-exhibitions section missing');
            }
            $newsBySlug=[];
            foreach($news['articles'] as $a)$newsBySlug[$a['slug']]=$a;
            $plans=[];
            foreach($src['exhibitions'] as $a){
                $path=$a['path']??'';$slug=$a['slug']??'';
                $node=$a['node_path']??'';
                $linked=$newsBySlug[$a['linked_news_slug']??'']??null;
                $proof=$linked ? ($linked['html']??'') : '';
                if(!preg_match('#^/vistavky/20\d{2}-\d\d-\d\d/[a-z0-9-]+$#D',$path)
                    || ($a['source_url']??null)!==self::SOURCE.$path
                    || !preg_match('#^/node/[0-9]+$#D',$node)
                    || !in_array($node,$a['node_paths']??[],true)
                    || $slug!=='museum-exhibit-'.str_replace('/','-',substr($path,strlen('/vistavky/')))
                    || ($a['category_slug']??null)!=='exhibitions-past'
                    || !is_string($a['title']??null) || mb_strlen($a['title'])<3
                    || !is_string($a['html']??null) || mb_strlen($a['html'])<8
                    || hash('sha256',$a['html'])!==($a['html_sha256']??null)
                    || !preg_match('/^[a-f0-9]{64}$/D',(string)($a['source_page_sha256']??''))
                    || stripos($a['html'],'<script')!==false || stripos($a['html'],'<img')!==false
                    || ($a['photos_rights_confirmed']??null)!==false
                    || !$linked
                    || ($a['linked_news_url']??null)!==($linked['source_url']??null)
                    || ($a['linked_news_html_sha256']??null)!==($linked['html_sha256']??null)
                    || hash('sha256',$proof)!==($linked['html_sha256']??null)
                    || !(str_contains($proof,self::SOURCE.$node) || str_contains($proof,'http://muzei-xleb.ru'.$node))
                    || isset($plans[$slug])){
                    throw new RuntimeException('Unverified original Drupal exhibition content '.$slug);
                }
                $existing=MuseumEntry::where('slug',$slug)->first();
                if($existing && ($existing->type!=='exhibition' || $existing->museum_section_id!==$section->id)){
                    throw new RuntimeException('Unrelated museum entry owns old exhibition slug '.$slug);
                }
                $plans[$slug]=['item'=>$a,'exists'=>$existing!==null];
                $this->line(($existing?'KEEP EDITOR':'NEW SOURCE-VERIFIED HISTORICAL DRAFT').' '.$slug);
            }
            if(count($plans)!==self::EXPECTED_ITEMS)throw new RuntimeException('Expected museum historical exhibition detail corpus incomplete');
            if(!$this->option('apply')){$this->info('Dry run successful, no museum data edited.');return self::SUCCESS;}
            DB::transaction(function()use($plans,$section){
                foreach($plans as $slug=>$plan){
                    $a=$plan['item'];$origin=htmlspecialchars($a['source_url'],ENT_QUOTES|ENT_SUBSTITUTE,'UTF-8');
                    MuseumEntry::firstOrCreate(['slug'=>$slug],[
                        'type'=>'exhibition','museum_section_id'=>$section->id,
                        'title'=>mb_substr($a['title'],0,255),'h1'=>mb_substr($a['title'],0,255),
                        'excerpt'=>$a['intro']?:null,
                        'body'=>$a['html'].'<p><a href="'.$origin.'">Подлинная публикация музея ↗</a></p>',
                        'status'=>'draft','published_at'=>null,
                    ]);
                }
            });
            $this->info(count($plans).' real historical museum exhibition texts imported as private drafts.');
            return self::SUCCESS;
        }catch(Throwable $err){
            $this->error('Original museum node-exhibition import rejected: '.$err->getMessage());
            return self::FAILURE;
        }
    }
}
