<?php

declare(strict_types=1);

namespace Tests\Feature;

use App\Models\MuseumEntry;
use Database\Seeders\ReferenceMuseumSectionsSeeder;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Artisan;
use Tests\TestCase;

final class ImportOfficialExhibitionsTest extends TestCase
{
    use RefreshDatabase;

    public function test_four_real_indexes_and_six_exhibition_pages_are_private_editable():void
    {
        $this->seed(ReferenceMuseumSectionsSeeder::class);
        $this->assertSame(0,Artisan::call('museum:import-official-exhibitions'));
        $this->assertDatabaseCount('museum_entries',0);
        $this->assertSame(0,Artisan::call('museum:import-official-exhibitions',['--apply'=>true]),Artisan::output());
        $this->assertDatabaseCount('museum_entries',10);
        $this->assertSame(6,MuseumEntry::where('type','exhibition')->count());
        $this->assertSame(10,MuseumEntry::where('status','draft')->count());
        $this->assertSame(0,MuseumEntry::whereNotNull('published_at')->count());
        $this->assertSame(2,MuseumEntry::where('type','exhibition')->whereHas('section',
            fn($q)=>$q->where('slug','exhibitions-current'))->count());
        $this->assertSame(4,MuseumEntry::where('type','exhibition')->whereHas('section',
            fn($q)=>$q->where('slug','exhibitions-traveling'))->count());
        foreach(MuseumEntry::all() as $entry){
            $this->assertSame(0,$entry->media()->count());
            $this->assertSame('exhibitions-guide',$entry->section->parent->slug);
        }
        $edited=MuseumEntry::where('type','exhibition')->firstOrFail();
        $edited->update(['title'=>'Новая версия редактора','body'=>'<p>Согласовано музеем.</p>']);
        $this->assertSame(0,Artisan::call('museum:import-official-exhibitions',['--apply'=>true]));
        $this->assertDatabaseCount('museum_entries',10);
        $this->assertSame('Новая версия редактора',$edited->fresh()->title);
        $this->assertSame('<p>Согласовано музеем.</p>',$edited->fresh()->body);
    }

    public function test_altered_original_document_fails_before_any_insert():void
    {
        $this->seed(ReferenceMuseumSectionsSeeder::class);
        $src=json_decode((string) file_get_contents(base_path('../web/src/data/official-exhibition-details.json')),true);
        $src['exhibitions'][1]['html']='<p>Это вымышленная выставка</p>';
        $path=storage_path('framework/testing/forged-exhibition.json');
        if(!is_dir(dirname($path)))mkdir(dirname($path),0700,true);
        file_put_contents($path,json_encode($src,JSON_UNESCAPED_UNICODE));
        try{
            $this->assertSame(1,Artisan::call('museum:import-official-exhibitions',
                ['--source'=>$path,'--apply'=>true]));
            $this->assertDatabaseCount('museum_entries',0);
        }finally{@unlink($path);}
    }

    public function test_editor_slug_ownership_and_production_guard():void
    {
        $this->seed(ReferenceMuseumSectionsSeeder::class);
        MuseumEntry::create(['slug'=>'exhibitions-current','type'=>'news',
            'title'=>'Новости','status'=>'draft','body'=>'<p>Другая рубрика.</p>']);
        $this->assertSame(1,Artisan::call('museum:import-official-exhibitions',['--apply'=>true]));
        $this->assertDatabaseCount('museum_entries',1);
        $old=app()->environment();
        app()->instance('env','production');
        try{
            $this->assertSame(1,Artisan::call('museum:import-official-exhibitions',['--apply'=>true]));
        }finally{app()->instance('env',$old);}
        $this->assertDatabaseCount('museum_entries',1);
    }
}
