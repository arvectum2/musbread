<?php

declare(strict_types=1);

namespace Tests\Feature;

use App\Models\MuseumEntry;
use Database\Seeders\ReferenceMuseumSectionsSeeder;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Artisan;
use Tests\TestCase;

final class ImportOfficialScienceTest extends TestCase
{
    use RefreshDatabase;

    public function test_two_original_institutional_documents_and_five_sections_are_private_drafts():void
    {
        $this->seed(ReferenceMuseumSectionsSeeder::class);
        $this->assertSame(0,Artisan::call('museum:import-official-science'));
        $this->assertDatabaseCount('museum_entries',0);
        $this->assertSame(0,Artisan::call('museum:import-official-science',['--apply'=>true]),Artisan::output());
        $this->assertDatabaseCount('museum_entries',7);
        $this->assertSame(7,MuseumEntry::where('type','page')->where('status','draft')->count());
        $this->assertSame(0,MuseumEntry::whereNotNull('published_at')->count());
        foreach(MuseumEntry::all() as $entry) {
            $this->assertSame('science',$entry->section->parent->slug);
            $this->assertSame(0,$entry->media()->count());
            $this->assertSame(0,$entry->documents()->count());
            $this->assertStringNotContainsString('история выдуманного экспоната', $entry->body);
        }
        $section=MuseumEntry::where('slug','science-collection')->firstOrFail();
        $this->assertStringContainsString('Госкаталог',$section->body);
        $this->assertStringContainsString('права на фотографии пока не предоставлены',$section->body);
        $research=MuseumEntry::where('slug','science-researchers')->firstOrFail();
        $this->assertStringContainsString('Отдельные правила работы внешних исследователей',$research->body);
        $source=MuseumEntry::where('slug','science-methodical-council')->firstOrFail();
        $this->assertSame('science-materials',$source->section->slug);
        $this->assertStringContainsString('Научно-методическ',$source->body);
        $source->update(['title'=>'Правка музейного редактора','body'=>'<p>Согласовано музейным научным отделом.</p>']);
        $this->assertSame(0,Artisan::call('museum:import-official-science',['--apply'=>true]));
        $this->assertDatabaseCount('museum_entries',7);
        $this->assertSame('Правка музейного редактора',$source->fresh()->title);
        $this->assertSame('<p>Согласовано музейным научным отделом.</p>',$source->fresh()->body);
    }

    public function test_forged_science_source_is_rejected_without_partial_writes():void
    {
        $this->seed(ReferenceMuseumSectionsSeeder::class);
        $source=json_decode((string)file_get_contents(base_path('../web/src/data/official-science-sources.json')),true);
        $source['pages'][1]['html']='<p>Несуществующая научная статья</p>';
        $path=storage_path('framework/testing/forged-science.json');
        if(!is_dir(dirname($path)))mkdir(dirname($path),0700,true);
        file_put_contents($path,json_encode($source,JSON_UNESCAPED_UNICODE));
        try{
            $this->assertSame(1,Artisan::call('museum:import-official-science',[
                '--apply'=>true,'--source'=>$path]));
            $this->assertDatabaseCount('museum_entries',0);
        }finally{@unlink($path);}
    }

    public function test_existing_unrelated_owner_and_production_bulk_import_denied():void
    {
        $this->seed(ReferenceMuseumSectionsSeeder::class);
        MuseumEntry::create(['slug'=>'science-organization','title'=>'Новость редактора',
            'body'=>'<p>Не научный раздел.</p>','type'=>'news','status'=>'draft']);
        $this->assertSame(1,Artisan::call('museum:import-official-science',['--apply'=>true]));
        $this->assertDatabaseCount('museum_entries',1);
        $old=app()->environment();
        app()->instance('env','production');
        try{
            $this->assertSame(1,Artisan::call('museum:import-official-science',['--apply'=>true]));
        }finally{app()->instance('env',$old);}
        $this->assertDatabaseCount('museum_entries',1);
    }
}
