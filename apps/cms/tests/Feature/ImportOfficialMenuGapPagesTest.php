<?php

declare(strict_types=1);

namespace Tests\Feature;

use App\Models\MuseumEntry;
use Database\Seeders\ReferenceMuseumSectionsSeeder;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Artisan;
use Tests\TestCase;

final class ImportOfficialMenuGapPagesTest extends TestCase
{
    use RefreshDatabase;

    public function test_real_original_legal_menu_pages_are_idempotent_private_editor_drafts():void
    {
        $this->seed(ReferenceMuseumSectionsSeeder::class);
        $this->assertSame(0,Artisan::call('museum:import-official-menu-gaps'),Artisan::output());
        $this->assertDatabaseCount('museum_entries',0);
        $this->assertSame(0,Artisan::call('museum:import-official-menu-gaps',['--apply'=>true]),Artisan::output());
        $this->assertDatabaseCount('museum_entries',3);
        foreach([
            'museum-accounting-policy'=>'Учетная политика',
            'museum-anti-terror'=>'Противодействие терроризму',
            'museum-antimonopoly'=>'Антимонопольный комплаенс',
        ] as $slug=>$title){
            $row=MuseumEntry::where('slug',$slug)->firstOrFail();
            $this->assertSame('draft',$row->status);
            $this->assertSame($slug,$row->section?->slug);
            $this->assertSame('page',$row->type);
            $this->assertSame($title,$row->title);
            $this->assertStringContainsString('https://muzei-xleb.ru/sites/default/files/page/',$row->body);
        }
        $row=MuseumEntry::where('slug','museum-accounting-policy')->firstOrFail();
        $this->assertSame(7,substr_count($row->body,'.pdf'));
        $row->update(['title'=>'Редактор уточнил заголовок']);
        $this->assertSame(0,Artisan::call('museum:import-official-menu-gaps',['--apply'=>true]),Artisan::output());
        $this->assertDatabaseCount('museum_entries',3);
        $this->assertSame('Редактор уточнил заголовок',$row->fresh()->title);
        $this->assertDatabaseCount('museum_documents',0);
    }

    public function test_invalid_capture_hash_cannot_create_any_article():void
    {
        $this->seed(ReferenceMuseumSectionsSeeder::class);
        $data=json_decode((string)file_get_contents(base_path('../web/src/data/official-museum-menu-gaps.json')),true);
        $data['pages'][0]['html'].='<p>Forged historical information</p>';
        $test=storage_path('framework/testing/forged-menu-gaps.json');
        if(!is_dir(dirname($test)))mkdir(dirname($test),0700,true);
        file_put_contents($test,json_encode($data,JSON_UNESCAPED_UNICODE));
        try {
            $this->assertSame(1,Artisan::call('museum:import-official-menu-gaps',[
                '--apply'=>true,'--source'=>$test,
            ]));
            $this->assertDatabaseCount('museum_entries',0);
        } finally { @unlink($test); }
    }

    public function test_production_import_refused():void
    {
        $this->seed(ReferenceMuseumSectionsSeeder::class);
        $before=app()->environment();
        app()->instance('env','production');
        try {
            $this->assertSame(1,Artisan::call('museum:import-official-menu-gaps',['--apply'=>true]));
        } finally { app()->instance('env',$before); }
        $this->assertDatabaseCount('museum_entries',0);
    }

    public function test_documents_mode_requires_explicit_apply():void
    {
        $this->seed(ReferenceMuseumSectionsSeeder::class);
        $this->assertSame(1,Artisan::call('museum:import-official-menu-gaps',['--documents'=>true]));
        $this->assertDatabaseCount('museum_documents',0);
    }
}
