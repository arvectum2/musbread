<?php

declare(strict_types=1);

namespace Tests\Feature;

use App\Models\MuseumEntry;
use App\Models\MuseumEvent;
use Database\Seeders\ReferenceMuseumSectionsSeeder;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Artisan;
use Tests\TestCase;

final class ImportOfficialNewsTest extends TestCase
{
    use RefreshDatabase;

    public function test_official_ten_source_news_and_one_proven_dated_event_are_private_editor_records():void
    {
        $this->seed(ReferenceMuseumSectionsSeeder::class);
        $this->assertSame(0,Artisan::call('museum:import-official-news'));
        $this->assertDatabaseCount('museum_entries',0);
        $this->assertDatabaseCount('museum_events',0);
        $this->assertSame(0,Artisan::call('museum:import-official-news',['--apply'=>true]),Artisan::output());
        $this->assertDatabaseCount('museum_entries',10);
        $this->assertDatabaseCount('museum_events',1);
        foreach(MuseumEntry::all() as $entry){
            $this->assertSame('news',$entry->type);
            $this->assertSame('draft',$entry->status);
            $this->assertNull($entry->published_at);
            $this->assertNull($entry->museum_section_id);
            $this->assertSame(0,$entry->media()->count());
        }
        $event=MuseumEvent::firstOrFail();
        $this->assertSame('museum-night-of-arts-2026',$event->slug);
        $this->assertSame('Музейное событие',$event->category);
        $this->assertSame('2026-11-03',$event->starts_at->format('Y-m-d'));
        $this->assertSame('2026-11-03',$event->ends_at->format('Y-m-d'));
        $this->assertSame('draft',$event->status);
        $this->assertNull($event->published_at);
        $this->assertSame('agenda-events',$event->section->slug);
        $this->assertStringContainsString('18:00–20:00',$event->body);
        $this->assertStringContainsString('https://muzei-xleb.ru/novosty/2026-10-16/noch-iskusstv-v-muzee-hleba',$event->body);
        $news=MuseumEntry::where('slug','museum-news-2026-10-16-noch-iskusstv-v-muzee-hleba')->firstOrFail();
        $news->update(['title'=>'Новость обновлена редактором','body'=>'<p>Согласованный пресс-релиз.</p>']);
        $event->update(['title'=>'Мероприятие изменено редактором']);
        $this->assertSame(0,Artisan::call('museum:import-official-news',['--apply'=>true]));
        $this->assertDatabaseCount('museum_entries',10);
        $this->assertDatabaseCount('museum_events',1);
        $this->assertSame('Новость обновлена редактором',$news->fresh()->title);
        $this->assertSame('Мероприятие изменено редактором',$event->fresh()->title);
    }

    public function test_forged_news_html_cannot_be_imported():void
    {
        $this->seed(ReferenceMuseumSectionsSeeder::class);
        $data=json_decode(file_get_contents(base_path('../web/src/data/official-museum-news.json')),true);
        $data['articles'][1]['html']='<p>Выдуманная новость</p>';
        $path=storage_path('framework/testing/forged-news.json');
        if(!is_dir(dirname($path)))mkdir(dirname($path),0700,true);
        file_put_contents($path,json_encode($data,JSON_UNESCAPED_UNICODE));
        try{
            $this->assertSame(1,Artisan::call('museum:import-official-news',
                ['--source'=>$path,'--apply'=>true]));
            $this->assertDatabaseCount('museum_entries',0);
            $this->assertDatabaseCount('museum_events',0);
        }finally{@unlink($path);}
    }

    public function test_news_slug_collision_and_production_seeding_refused():void
    {
        $this->seed(ReferenceMuseumSectionsSeeder::class);
        MuseumEntry::create(['slug'=>'museum-news-2026-10-16-noch-iskusstv-v-muzee-hleba',
            'title'=>'Чужой редактор','type'=>'page','body'=>'<p>Другой тип.</p>','status'=>'draft']);
        $this->assertSame(1,Artisan::call('museum:import-official-news',['--apply'=>true]));
        $this->assertDatabaseCount('museum_entries',1);
        $this->assertDatabaseCount('museum_events',0);
        $previous=app()->environment();
        app()->instance('env','production');
        try{$this->assertSame(1,Artisan::call('museum:import-official-news',['--apply'=>true]));}
        finally{app()->instance('env',$previous);}
    }
}
