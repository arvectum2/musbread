<?php
declare(strict_types=1);

namespace Tests\Feature;

use App\Models\MuseumEntry;
use Database\Seeders\ReferenceMuseumSectionsSeeder;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Artisan;
use Tests\TestCase;

final class ImportOfficialSeminarsTest extends TestCase
{
    use RefreshDatabase;

    public function test_dry_run_then_seven_private_science_editor_drafts_and_idempotency():void
    {
        $this->seed(ReferenceMuseumSectionsSeeder::class);
        $this->assertSame(0,Artisan::call('museum:import-official-seminars'),Artisan::output());
        $this->assertDatabaseCount('museum_entries',0);
        $this->assertSame(0,Artisan::call('museum:import-official-seminars',['--apply'=>true]),Artisan::output());
        $this->assertDatabaseCount('museum_entries',7);
        $this->assertSame(7,MuseumEntry::where('status','draft')->whereNull('published_at')->count());
        foreach(MuseumEntry::all() as $entry){
            $this->assertSame('page',$entry->type);
            $this->assertSame('science-conferences',$entry->section->slug);
            $this->assertStringContainsString('https://muzei-xleb.ru/seminar-',$entry->body);
            $this->assertSame(0,$entry->media()->count());
            $this->assertSame(0,$entry->documents()->count());
        }
        $one=MuseumEntry::where('slug','science-seminar-2026-04-16-633')->firstOrFail();
        $this->assertStringContainsString('мукомольных мельниц',$one->title);
        $one->update(['title'=>'Утверждённая редакция музея','body'=>'<p>Редактор проверил материал.</p>']);
        $this->assertSame(0,Artisan::call('museum:import-official-seminars',['--apply'=>true]),Artisan::output());
        $this->assertDatabaseCount('museum_entries',7);
        $this->assertSame('Утверждённая редакция музея',$one->fresh()->title);
        $this->assertSame('<p>Редактор проверил материал.</p>',$one->fresh()->body);
    }

    public function test_forged_source_metadata_refused_and_keeps_db_untouched():void
    {
        $this->seed(ReferenceMuseumSectionsSeeder::class);
        $data=json_decode((string)file_get_contents(base_path('../web/src/data/official-museum-seminars.json')),true);
        $data['seminars'][0]['date_start']='2026-04-17';
        $path=storage_path('framework/testing/forged-museum-seminar.json');
        if(!is_dir(dirname($path)))mkdir(dirname($path),0700,true);
        file_put_contents($path,json_encode($data,JSON_UNESCAPED_UNICODE));
        try{
            $this->assertSame(1,Artisan::call('museum:import-official-seminars',
                ['--apply'=>true,'--source'=>$path]));
            $this->assertDatabaseCount('museum_entries',0);
        }finally{@unlink($path);}
    }

    public function test_production_bulk_seminar_import_is_disabled():void
    {
        $this->seed(ReferenceMuseumSectionsSeeder::class);
        $before=app()->environment();
        app()->instance('env','production');
        try{$this->assertSame(1,Artisan::call('museum:import-official-seminars',['--apply'=>true]));}
        finally{app()->instance('env',$before);}
        $this->assertDatabaseCount('museum_entries',0);
    }
}
