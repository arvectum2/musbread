<?php

namespace App\Console\Commands;

use App\Models\MuseumEntry;
use App\Models\MuseumSection;
use Illuminate\Console\Command;
use Illuminate\Support\Facades\DB;
use RuntimeException;
use Throwable;

/**
 * Only five truthful scientific-section landings + two actually published
 * scientific administration records, without fictional publications,
 * conferences, inventory objects or research permissions.
 */
final class ImportOfficialScience extends Command
{
    protected $signature='museum:import-official-science
        {--apply : Create five science landing drafts and two source-verified materials}
        {--source= : Override source JSON for deterministic QA}';
    protected $description='Prepare verified scientific-organization materials and empty editor-ready science sections';

    private const SOURCE_DIGESTS=[
        'science-organization'=>'0bbe545eb5098c7411efac6114517010cbdd0aaa07c62bfec8e081a278d77dd8',
        'science-methodical-council'=>'99c56d681dd86f4dfab5672e01af6020a3fe2cb8e791659f245a4ce9a3e74efe',
    ];
    private const DOCUMENTS=[
        'science-organization'=>'https://muzei-xleb.ru/sites/default/files/page/20260203111659-koncepciya_komplektovaniya_mh.pdf',
        'science-methodical-council'=>'https://muzei-xleb.ru/sites/default/files/page/polozhenie_o_nauchno-metodicheskom_sovete_spb_gbuk_sankt-peterburgskiy_muzey_hleba.docx',
    ];
    private const SECTIONS=[
        'science-conferences'=>[
            'Семинары и конференции',
            'Официальные анонсы научных мероприятий пока не подтверждены. Редактор музея сможет публиковать семинары и конференции через штатную афишу.',
        ],
        'science-publications'=>[
            'Научные публикации',
            'Для заполнения библиографии необходимы проверенные авторы, названия, выходные данные и права на материалы. Организационные положения не классифицируются как научные публикации.',
        ],
        'science-collection'=>[
            'Коллекция музея',
            'На действующем сайте музея есть ссылка на его раздел Госкаталога. Отдельные музейные предметы, инвентарные номера и права на фотографии пока не предоставлены.',
        ],
        'science-researchers'=>[
            'Исследователям',
            'На сайте музея размещено положение о порядке и условиях доступа граждан к музейным предметам и коллекциям. Отдельные правила работы внешних исследователей необходимо уточнить в музее.',
        ],
        'science-materials'=>[
            'Материалы по теме',
            'В разделе представлены только подтверждённые организационные документы: концепция комплектования фондов и положение о научно-методическом совете. Это не библиография научных публикаций.',
        ],
    ];

    public function handle():int
    {
        if($this->option('apply') && app()->environment('production')){
            $this->error('Source bulk import disabled in production; release only through editorial CMS.');
            return self::FAILURE;
        }
        try{
            $path=$this->option('source') ?: base_path('../web/src/data/official-science-sources.json');
            $data=json_decode((string)file_get_contents($path),true,flags:JSON_THROW_ON_ERROR);
            if(($data['source']??null)!=='https://muzei-xleb.ru'
                || ($data['count']??null)!==2 || !is_array($data['pages']??null)
                || count($data['pages'])!==2){
                throw new RuntimeException('Unexpected museum scientific-organization document count');
            }
            $sections=[];
            foreach(self::SECTIONS as $slug=>$values){
                $section=MuseumSection::where('slug',$slug)->first();
                if(!$section || $section->parent?->slug!=='science'||$section->legacy_path!==null){
                    throw new RuntimeException('Missing expected science section: '.$slug);
                }
                $existing=MuseumEntry::where('slug',$slug)->first();
                if($existing && ($existing->type!=='page'||$existing->museum_section_id!==$section->id)){
                    throw new RuntimeException('Science landing slug belongs to another editor: '.$slug);
                }
                $sections[$slug]=compact('section','existing');
            }
            $items=[];$seen=[];
            foreach($data['pages'] as $item){
                $slug=$item['slug']??'';
                $digest=self::SOURCE_DIGESTS[$slug]??null;
                $url='https://muzei-xleb.ru'.($item['path']??'');
                if(!$digest||isset($seen[$slug])
                    || ($item['source_url']??null)!==$url
                    || !in_array($item['path'],[
                        '/nauchno-organizacionnaya-deyatelnost',
                        '/nauchno-metodicheskiy-sovet'],true)
                    || ($item['html_sha256']??null)!==$digest
                    || !is_string($item['html']??null)
                    || hash('sha256',$item['html'])!==$digest
                    || ($item['photos_rights_confirmed']??null)!==false
                    || ($item['text_length']??0)<80
                    || !is_array($item['documents']??null)
                    || count($item['documents'])!==1
                    || ($item['documents'][0]['url']??null)!==self::DOCUMENTS[$slug]
                    || !is_string($item['title']??null)||mb_strlen($item['title'])<8){
                    throw new RuntimeException('Scientific material source verification failed: '.$slug);
                }
                $existing=MuseumEntry::where('slug',$slug)->first();
                if($existing && ($existing->type!=='page'
                    ||$existing->museum_section_id!==$sections['science-materials']['section']->id)){
                    throw new RuntimeException('Existing source slug belongs to another editor: '.$slug);
                }
                $seen[$slug]=true;
                $items[$slug]=compact('item','existing');
            }
            if(count($items)!==2)throw new RuntimeException('Both original scientific material documents required');
            foreach($sections as $slug=>$row){
                $this->line(($row['existing']?'KEEP EDITOR':'NEW DRAFT').' '.$slug);
            }
            foreach($items as $slug=>$row){
                $this->line(($row['existing']?'KEEP EDITOR':'NEW SOURCE DRAFT').' '.$slug);
            }
            if(!$this->option('apply')){
                $this->info('Dry run: no publications or invented academic materials created.');
                return self::SUCCESS;
            }
            DB::transaction(function()use($sections,$items){
                foreach(self::SECTIONS as $slug=>$values){
                    MuseumEntry::firstOrCreate(['slug'=>$slug],[
                        'museum_section_id'=>$sections[$slug]['section']->id,
                        'type'=>'page','title'=>$values[0],'h1'=>$values[0],
                        'excerpt'=>$values[1],
                        'body'=>'<p>'.$values[1].'</p>',
                        'status'=>'draft','published_at'=>null,
                    ]);
                }
                foreach($items as $slug=>$row){
                    $item=$row['item'];
                    $doc=$item['documents'][0];
                    $url=htmlspecialchars($doc['url'],ENT_QUOTES|ENT_SUBSTITUTE,'UTF-8');
                    $label=htmlspecialchars($doc['label'],ENT_QUOTES|ENT_SUBSTITUTE,'UTF-8');
                    MuseumEntry::firstOrCreate(['slug'=>$slug],[
                        'museum_section_id'=>$sections['science-materials']['section']->id,
                        'type'=>'page','title'=>$item['title'],'h1'=>$item['title'],
                        'excerpt'=>'Официальный источник: '.$item['source_url'],
                        'body'=>$item['html'].'<p><a href="'.$url.'">'.$label.'</a></p>',
                        'status'=>'draft','published_at'=>null,
                    ]);
                }
            });
            $this->info('Five science landing drafts plus two verified source material drafts. No academic paper, specimen or conference invented.');
            return self::SUCCESS;
        }catch(Throwable $error){
            $this->error('Scientific material import refused: '.$error->getMessage());
            return self::FAILURE;
        }
    }
}
