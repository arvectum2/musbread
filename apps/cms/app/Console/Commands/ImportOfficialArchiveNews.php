<?php

declare(strict_types=1);

namespace App\Console\Commands;

use App\Models\MuseumEntry;
use Illuminate\Console\Command;
use Illuminate\Support\Facades\DB;
use RuntimeException;
use Throwable;

/** Historical original museum news, not future events or offers of tickets. */
final class ImportOfficialArchiveNews extends Command
{
    protected $signature='museum:import-official-archive-news
        {--apply : Import genuine historical news only as private draft entries}
        {--source= : Local archive JSON for source validation tests}';
    protected $description='Source-checked archived museum news, preserve editor changes and never publish';

    // Captured live index page URLs + exact original article HTML hashes.
    // Updated only after a fresh independently verified museum snapshot.
    private const SOURCE_SET_DIGEST='1a2dd55f55cd7077b1c34f2499a3bebfcfa3ad52289c02cc48e2931621b99f0a';
    private const SOURCE='https://muzei-xleb.ru';

    public function handle():int
    {
        if ($this->option('apply') && app()->environment('production')) {
            $this->error('Bulk official news archive import forbidden in production.');
            return self::FAILURE;
        }
        try {
            $path=(string)($this->option('source')
                ?:base_path('../web/src/data/official-museum-news-archive.json'));
            $data=json_decode((string)file_get_contents($path),true,flags:JSON_THROW_ON_ERROR);
            $indices=$data['indices']??null;
            $articles=$data['articles']??null;
            if (($data['source']??null)!==self::SOURCE || ($data['count']??null)!==20
                || !is_array($indices) || count($indices)!==2
                || !is_array($articles) || count($articles)!==20) {
                throw new RuntimeException('Original museum archive snapshot missing or incomplete');
            }
            $indexed=[];
            foreach([1,2] as $offset=>$page) {
                $index=$indices[$offset];
                if (($index['url']??null)!==self::SOURCE.'/novosty?page='.$page
                    || !preg_match('/^[a-f0-9]{64}$/D',(string)($index['source_listing_sha256']??''))
                    || !is_array($index['article_paths']??null)
                    || count($index['article_paths'])!==10) {
                    throw new RuntimeException('Archival news list mismatch');
                }
                foreach($index['article_paths'] as $articlePath) {
                    if (isset($indexed[$articlePath]))throw new RuntimeException('Duplicate archive link');
                    $indexed[$articlePath]=$page;
                }
            }
            $set=[];
            foreach($articles as $article) {
                $set[]=($article['source_url']??'').'|'.($article['html_sha256']??'');
            }
            if (hash('sha256',implode("\n",$set))!==self::SOURCE_SET_DIGEST) {
                throw new RuntimeException('Known original archive page signatures mismatch');
            }
            $latest=json_decode((string)file_get_contents(
                base_path('../web/src/data/official-museum-news.json')),true,flags:JSON_THROW_ON_ERROR);
            $current=array_fill_keys(array_column($latest['articles']??[],'slug'),true);
            $plans=[];
            foreach($articles as $article) {
                $path=$article['path']??'';
                $date=$article['published_on']??'';
                $slug=$article['slug']??'';
                if(!preg_match('#^/novosty/(20\d{2}-\d\d-\d\d)/([a-z0-9-]+)$#D',$path,$match)
                    || $date!==$match[1]
                    || $slug!=='museum-news-'.$date.'-'.$match[2]
                    || ($article['source_url']??'')!==self::SOURCE.$path
                    || ($article['archive_index_page']??null)!==($indexed[$path]??null)
                    || ($article['photos_rights_confirmed']??null)!==false
                    || !is_string($article['title']??null) || mb_strlen($article['title'])<8
                    || !is_string($article['intro']??null) || mb_strlen($article['intro'])<18
                    || !is_string($article['html']??null) || mb_strlen($article['html'])<30
                    || hash('sha256',$article['html'])!==($article['html_sha256']??'')
                    || stripos($article['html'],'<img')!==false
                    || stripos($article['html'],'<script')!==false
                    || isset($plans[$slug]) || isset($current[$slug])) {
                    throw new RuntimeException('Museum historical news page provenance mismatch: '.$slug);
                }
                $existing=MuseumEntry::where('slug',$slug)->first();
                if ($existing && ($existing->type!=='news' || $existing->museum_section_id!==null)) {
                    throw new RuntimeException('Unrelated existing entry owns historical source slug: '.$slug);
                }
                $plans[$slug]=['item'=>$article,'exists'=>$existing!==null];
                $this->line(($existing?'KEEP EDITOR':'NEW PRIVATE ARCHIVE').' '.$slug);
            }
            if (count($plans)!==20 || count($indexed)!==20) {
                throw new RuntimeException('Incomplete original museum archive linkage');
            }
            if (!$this->option('apply')) {
                $this->info('Dry run: archive original and editorial data unchanged.');
                return self::SUCCESS;
            }
            DB::transaction(function() use($plans):void {
                foreach($plans as $slug=>$row) {
                    $i=$row['item'];
                    $url=htmlspecialchars($i['source_url'],ENT_QUOTES|ENT_SUBSTITUTE,'UTF-8');
                    MuseumEntry::firstOrCreate(['slug'=>$slug],[
                        'type'=>'news','museum_section_id'=>null,
                        'title'=>mb_substr($i['title'],0,255),
                        'h1'=>mb_substr($i['title'],0,255),
                        'excerpt'=>$i['intro'],
                        'body'=>$i['html'].'<p><a href="'.$url.'">Исходная архивная публикация музея ↗</a></p>',
                        'status'=>'draft','published_at'=>null,
                    ]);
                }
            });
            $this->info('20 source-backed museum historical news drafts; no events, media or bookings created.');
            return self::SUCCESS;
        } catch (Throwable $e) {
            $this->error('Original museum archive import refused: '.$e->getMessage());
            return self::FAILURE;
        }
    }
}
