<?php

declare(strict_types=1);

namespace Tests\Feature;

use App\Models\MuseumEntry;
use Database\Seeders\ReferenceMuseumSectionsSeeder;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Artisan;
use Tests\TestCase;

final class ImportOfficialWorkshopsTest extends TestCase
{
    use RefreshDatabase;

    public function test_twelve_original_workshops_and_two_landings_remain_editor_owned_drafts():void
    {
        $this->seed(ReferenceMuseumSectionsSeeder::class);
        $this->assertSame(0,Artisan::call('museum:import-official-workshops'));
        $this->assertDatabaseCount('museum_entries',0);
        $this->assertSame(0,Artisan::call('museum:import-official-workshops',['--apply'=>true]),Artisan::output());
        $this->assertDatabaseCount('museum_entries',14);
        $programs=MuseumEntry::where('slug','like','museum-workshop-%')->get();
        $this->assertCount(12,$programs);
        foreach($programs as $item){
            $this->assertSame('page',$item->type);
            $this->assertSame('draft',$item->status);
            $this->assertNull($item->published_at);
            $this->assertSame('children-workshops',$item->section->slug);
            $this->assertGreaterThan(40,mb_strlen($item->excerpt));
            $this->assertStringContainsString('Официальное описание мастер-класса',$item->body);
            $this->assertSame(0,$item->media()->count());
        }
        $adult=MuseumEntry::where('slug','excursion-workshops-adults')->firstOrFail();
        $this->assertSame('draft',$adult->status);
        $this->assertStringContainsString('Участие взрослых уточняйте',$adult->body);
        $child=MuseumEntry::where('slug','children-workshops')->firstOrFail();
        $this->assertSame('draft',$child->status);
        $this->assertStringContainsString('12 мастер-классов',$child->body);
        $first=$programs->first();
        $first->update(['title'=>'Редактор изменил название','body'=>'<p>Редактор сохранил версию.</p>']);
        $this->assertSame(0,Artisan::call('museum:import-official-workshops',['--apply'=>true]));
        $this->assertDatabaseCount('museum_entries',14);
        $this->assertSame('Редактор изменил название',$first->fresh()->title);
        $this->assertSame('<p>Редактор сохранил версию.</p>',$first->fresh()->body);
    }

    public function test_forged_source_is_rejected_without_partial_writes():void
    {
        $this->seed(ReferenceMuseumSectionsSeeder::class);
        $data=json_decode(file_get_contents(base_path('../web/src/data/official-workshop-pages.json')),true);
        $data['programs'][0]['title']='Выдуманный мастер-класс';
        $data['programs'][0]['html']='<p>Другая несуществующая программа</p>';
        $path=storage_path('framework/testing/forged-workshops.json');
        if(!is_dir(dirname($path)))mkdir(dirname($path),0700,true);
        file_put_contents($path,json_encode($data,JSON_UNESCAPED_UNICODE));
        try {
            $this->assertSame(1,Artisan::call('museum:import-official-workshops',[
                '--apply'=>true,'--source'=>$path,
            ]));
            $this->assertDatabaseCount('museum_entries',0);
        }finally{@unlink($path);}
    }

    public function test_unrelated_editor_collision_and_production_seed_are_rejected():void
    {
        $this->seed(ReferenceMuseumSectionsSeeder::class);
        MuseumEntry::create(['slug'=>'museum-workshop-kukly-kuvadki','type'=>'news',
            'title'=>'Чужое','status'=>'draft','body'=>'<p>Не мастер-класс</p>']);
        $this->assertSame(1,Artisan::call('museum:import-official-workshops',['--apply'=>true]));
        $this->assertDatabaseCount('museum_entries',1);
        $old=app()->environment();
        app()->instance('env','production');
        try {
            $this->assertSame(1,Artisan::call('museum:import-official-workshops',['--apply'=>true]));
        }finally{app()->instance('env',$old);}
        $this->assertDatabaseCount('museum_entries',1);
    }
}
