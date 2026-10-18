<?php

declare(strict_types=1);
namespace Tests\Feature;

use App\Models\MuseumEntry;
use Database\Seeders\ReferenceMuseumSectionsSeeder;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Artisan;
use Tests\TestCase;

final class ImportOfficialNewsLinkedExhibitionsTest extends TestCase
{
    use RefreshDatabase;

    public function test_source_linked_past_exhibitions_are_private_idempotent_and_editor_editable():void
    {
        $this->seed(ReferenceMuseumSectionsSeeder::class);
        $this->assertSame(0,Artisan::call('museum:import-official-news-linked-exhibitions'),Artisan::output());
        $this->assertDatabaseCount('museum_entries',0);
        $this->assertSame(0,Artisan::call('museum:import-official-news-linked-exhibitions',[
            '--apply'=>true,
        ]),Artisan::output());
        $this->assertDatabaseCount('museum_entries',2);
        $this->assertSame(2,MuseumEntry::where('type','exhibition')->where('status','draft')->count());
        $this->assertSame(2,MuseumEntry::whereHas('section',
            static fn($q)=>$q->where('slug','exhibitions-past'))->count());
        $this->assertDatabaseCount('museum_media',0);
        $this->assertDatabaseCount('museum_events',0);
        $editor=MuseumEntry::firstOrFail();
        $editor->update(['title'=>'Согласованная редакция музея']);
        $this->assertSame(0,Artisan::call('museum:import-official-news-linked-exhibitions',[
            '--apply'=>true,
        ]),Artisan::output());
        $this->assertDatabaseCount('museum_entries',2);
        $this->assertSame('Согласованная редакция музея',$editor->fresh()->title);
    }

    public function test_fabricated_source_exhibition_is_rejected_before_any_insert():void
    {
        $this->seed(ReferenceMuseumSectionsSeeder::class);
        $src=json_decode((string)file_get_contents(
            base_path('../web/src/data/official-exhibition-news-linked.json')),true);
        $src['exhibitions'][1]['html'].='<script>invented-exhibition()</script>';
        $path=storage_path('framework/testing/forged-news-linked-exhibitions.json');
        if(!is_dir(dirname($path)))mkdir(dirname($path),0700,true);
        file_put_contents($path,json_encode($src,JSON_UNESCAPED_UNICODE));
        try {
            $this->assertSame(1,Artisan::call('museum:import-official-news-linked-exhibitions',[
                '--source'=>$path,'--apply'=>true,
            ]));
            $this->assertDatabaseCount('museum_entries',0);
        }finally{@unlink($path);}
    }
}
