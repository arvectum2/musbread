<?php

declare(strict_types=1);

namespace Tests\Feature;

use App\Models\MuseumEntry;
use Database\Seeders\ReferenceMuseumSectionsSeeder;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Artisan;
use Tests\TestCase;

final class ImportOfficialExhibitionArchiveTest extends TestCase
{
    use RefreshDatabase;

    public function test_source_verified_24_archived_and_virtual_exhibitions_stay_draft_and_idempotent():void
    {
        $this->seed(ReferenceMuseumSectionsSeeder::class);
        $this->assertSame(0,Artisan::call('museum:import-official-exhibition-archive'),Artisan::output());
        $this->assertDatabaseCount('museum_entries',0);
        $this->assertSame(0,Artisan::call('museum:import-official-exhibition-archive',[
            '--apply'=>true,
        ]),Artisan::output());
        $this->assertDatabaseCount('museum_entries',24);
        $this->assertSame(12,MuseumEntry::where('type','exhibition')->whereHas('section',
            fn($q)=>$q->where('slug','exhibitions-past'))->count());
        $this->assertSame(12,MuseumEntry::where('type','exhibition')->whereHas('section',
            fn($q)=>$q->where('slug','exhibitions-virtual'))->count());
        $this->assertSame(24,MuseumEntry::where('status','draft')->count());
        $this->assertDatabaseCount('museum_media',0);
        $this->assertDatabaseCount('museum_events',0);
        $edited=MuseumEntry::where('type','exhibition')->firstOrFail();
        $edited->update(['title'=>'Точное согласованное название музея','body'=>'<p>Редакторская версия.</p>']);
        $this->assertSame(0,Artisan::call('museum:import-official-exhibition-archive',[
            '--apply'=>true,
        ]),Artisan::output());
        $this->assertDatabaseCount('museum_entries',24);
        $this->assertSame('Точное согласованное название музея',$edited->fresh()->title);
    }

    public function test_original_source_tampering_and_wrong_existing_slug_are_rejected():void
    {
        $this->seed(ReferenceMuseumSectionsSeeder::class);
        $src=json_decode((string)file_get_contents(
            base_path('../web/src/data/official-exhibition-archive.json')),true);
        $src['exhibitions'][0]['html'].='<script>invented()</script>';
        $path=storage_path('framework/testing/tampered-exhibition-archive.json');
        try {
            file_put_contents($path,json_encode($src,JSON_UNESCAPED_UNICODE));
            $this->assertSame(1,Artisan::call('museum:import-official-exhibition-archive',[
                '--source'=>$path,'--apply'=>true,
            ]));
            $this->assertDatabaseCount('museum_entries',0);
        } finally {@unlink($path);}
        $original=json_decode((string)file_get_contents(
            base_path('../web/src/data/official-exhibition-archive.json')),true);
        MuseumEntry::create([
            'slug'=>$original['exhibitions'][0]['slug'],
            'type'=>'news','status'=>'draft','title'=>'Другая запись редактора',
            'body'=>'<p>Чужой редакторский объект.</p>',
        ]);
        $this->assertSame(1,Artisan::call('museum:import-official-exhibition-archive',[
            '--apply'=>true,
        ]));
        $this->assertDatabaseCount('museum_entries',1);
    }
}
