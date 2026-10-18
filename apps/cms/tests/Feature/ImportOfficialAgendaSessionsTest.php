<?php

declare(strict_types=1);

namespace Tests\Feature;

use App\Models\MuseumEvent;
use Database\Seeders\ReferenceMuseumSectionsSeeder;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Artisan;
use Tests\TestCase;

final class ImportOfficialAgendaSessionsTest extends TestCase
{
    use RefreshDatabase;

    public function test_124_dated_museum_sessions_are_all_private_editor_drafts():void
    {
        $this->seed(ReferenceMuseumSectionsSeeder::class);
        $this->assertSame(0,Artisan::call('museum:import-official-agenda'));
        $this->assertDatabaseCount('museum_events',0);
        $this->assertSame(0,Artisan::call('museum:import-official-agenda',['--apply'=>true]),Artisan::output());
        $this->assertDatabaseCount('museum_events',124);
        $this->assertSame(124,MuseumEvent::where('status','draft')->whereNull('published_at')->count());
        $this->assertSame(100,MuseumEvent::where('category','Экскурсия')->count());
        $this->assertSame(15,MuseumEvent::where('category','Мастер-класс')->count());
        $this->assertSame(2,MuseumEvent::where('category','Литературная гостиная')->count());
        $this->assertSame(4,MuseumEvent::where('category','Интерактивное занятие')->count());
        $this->assertSame(3,MuseumEvent::where('category','Тематическая программа')->count());
        foreach(MuseumEvent::all() as $e){
            $this->assertSame('agenda',$e->section->parent->slug);
            $this->assertSame($e->starts_at->format('Y-m-d'),$e->ends_at->format('Y-m-d'));
            $this->assertNull($e->cover_media_id);
            $this->assertStringContainsString('https://muzei-xleb.ru/novosty/',$e->body);
        }
        $one=MuseumEvent::where('category','Экскурсия')->firstOrFail();
        $one->update(['title'=>'Редактор исправил текст афиши','body'=>'<p>Проверенная редактором программа.</p>']);
        $this->assertSame(0,Artisan::call('museum:import-official-agenda',['--apply'=>true]));
        $this->assertDatabaseCount('museum_events',124);
        $this->assertSame('Редактор исправил текст афиши',$one->fresh()->title);
        $this->assertSame('<p>Проверенная редактором программа.</p>',$one->fresh()->body);
    }

    public function test_forged_session_refused_with_no_partial_writes():void
    {
        $this->seed(ReferenceMuseumSectionsSeeder::class);
        $source=json_decode((string)file_get_contents(base_path('../web/src/data/official-agenda-sessions.json')),true);
        $source['sessions'][4]['time']='19:13';
        $path=storage_path('framework/testing/forged-agenda-session.json');
        if(!is_dir(dirname($path)))mkdir(dirname($path),0700,true);
        file_put_contents($path,json_encode($source,JSON_UNESCAPED_UNICODE));
        try{
            $this->assertSame(1,Artisan::call('museum:import-official-agenda',
                ['--apply'=>true,'--source'=>$path]));
            $this->assertDatabaseCount('museum_events',0);
        }finally{@unlink($path);}
    }

    public function test_production_guard_requires_individual_editorial_approval():void
    {
        $this->seed(ReferenceMuseumSectionsSeeder::class);
        $old=app()->environment();
        app()->instance('env','production');
        try{$this->assertSame(1,Artisan::call('museum:import-official-agenda',['--apply'=>true]));}
        finally{app()->instance('env',$old);}
        $this->assertDatabaseCount('museum_events',0);
    }
}
