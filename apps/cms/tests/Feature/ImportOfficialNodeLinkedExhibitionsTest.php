<?php

declare(strict_types=1);
namespace Tests\Feature;
use App\Models\MuseumEntry;
use Database\Seeders\ReferenceMuseumSectionsSeeder;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Artisan;
use Tests\TestCase;

final class ImportOfficialNodeLinkedExhibitionsTest extends TestCase
{
    use RefreshDatabase;

    public function test_real_old_drupal_node_exhibition_corpus_imports_as_private_drafts_only():void
    {
        $this->seed(ReferenceMuseumSectionsSeeder::class);
        $source=json_decode((string)file_get_contents(
            base_path('../web/src/data/official-node-linked-exhibitions.json')),true);
        $expected=$source['new_exhibition_count'];
        $this->assertGreaterThan(15,$expected);
        $this->assertSame(61,$source['node_count']);
        $this->assertSame(0,Artisan::call('museum:import-official-node-linked-exhibitions'),Artisan::output());
        $this->assertDatabaseCount('museum_entries',0);
        $this->assertSame(0,Artisan::call('museum:import-official-node-linked-exhibitions',[
            '--apply'=>true,
        ]),Artisan::output());
        $this->assertDatabaseCount('museum_entries',$expected);
        $this->assertSame($expected,MuseumEntry::where('type','exhibition')->where('status','draft')->count());
        $this->assertDatabaseCount('museum_media',0);
        $this->assertDatabaseCount('museum_events',0);
        $entry=MuseumEntry::firstOrFail();
        $entry->update(['title'=>'Согласованная редакция музея']);
        $this->assertSame(0,Artisan::call('museum:import-official-node-linked-exhibitions',[
            '--apply'=>true,
        ]),Artisan::output());
        $this->assertSame('Согласованная редакция музея',$entry->fresh()->title);
        $this->assertDatabaseCount('museum_entries',$expected);
    }

    public function test_tampered_original_linked_exhibition_is_rejected_before_any_insert():void
    {
        $this->seed(ReferenceMuseumSectionsSeeder::class);
        $source=json_decode((string)file_get_contents(
            base_path('../web/src/data/official-node-linked-exhibitions.json')),true);
        $source['exhibitions'][0]['html'].='<script>fake-source()</script>';
        $file=storage_path('framework/testing/forged-museum-node-exhibitions.json');
        if(!is_dir(dirname($file)))mkdir(dirname($file),0700,true);
        file_put_contents($file,json_encode($source,JSON_UNESCAPED_UNICODE));
        try {
            $this->assertSame(1,Artisan::call('museum:import-official-node-linked-exhibitions',[
                '--apply'=>true,'--source'=>$file,
            ]));
            $this->assertDatabaseCount('museum_entries',0);
        }finally{@unlink($file);}
    }
}
