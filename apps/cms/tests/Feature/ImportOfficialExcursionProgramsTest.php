<?php

declare(strict_types=1);

namespace Tests\Feature;

use App\Models\MuseumEntry;
use Database\Seeders\ReferenceMuseumSectionsSeeder;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Artisan;
use Tests\TestCase;

final class ImportOfficialExcursionProgramsTest extends TestCase
{
    use RefreshDatabase;

    public function test_imports_seventeen_source_provenance_excursions_as_private_cms_drafts(): void
    {
        $this->seed(ReferenceMuseumSectionsSeeder::class);
        $this->assertSame(0, Artisan::call('museum:import-official-excursion-programs'));
        $this->assertDatabaseCount('museum_entries',0);
        $this->assertSame(0, Artisan::call('museum:import-official-excursion-programs',[
            '--apply'=>true,
        ]),Artisan::output());
        $this->assertDatabaseCount('museum_entries',17);
        $this->assertSame(17,MuseumEntry::where('type','excursion')->where('status','draft')->count());
        $this->assertSame(0,MuseumEntry::where('type','excursion')->whereNotNull('published_at')->count());
        $this->assertSame(6,MuseumEntry::whereHas('section',fn($q)=>$q->where('slug','excursion-interactive'))->count());
        $this->assertSame(9,MuseumEntry::whereHas('section',fn($q)=>$q->where('slug','excursion-thematic'))->count());
        $this->assertSame(2,MuseumEntry::whereHas('section',fn($q)=>$q->where('slug','excursion-theatrical'))->count());
        foreach (MuseumEntry::where('type','excursion')->get() as $entry) {
            $this->assertGreaterThan(40, mb_strlen($entry->excerpt));
            $this->assertStringContainsString('Официальный музейный первоисточник программы', $entry->body);
            $this->assertSame(0,$entry->media()->count());
            $this->assertSame(0,$entry->documents()->count());
            $this->assertMatchesRegularExpression('/^museum-tour-[a-z0-9-]+$/',$entry->slug);
        }
        $edit=MuseumEntry::where('slug','museum-tour-kolobok')->firstOrFail();
        $edit->update(['body'=>'<p>Редакция музея.</p>', 'title'=>'Уточнённое название']);
        $this->assertSame(0,Artisan::call('museum:import-official-excursion-programs',['--apply'=>true]));
        $this->assertDatabaseCount('museum_entries',17);
        $this->assertSame('<p>Редакция музея.</p>',$edit->fresh()->body);
        $this->assertSame('Уточнённое название',$edit->fresh()->title);
    }

    public function test_source_edits_or_duplicate_entries_are_rejected_before_writing(): void
    {
        $this->seed(ReferenceMuseumSectionsSeeder::class);
        $data=json_decode((string) file_get_contents(base_path('../web/src/data/official-excursion-programs.json')),true);
        $data['programs'][0]['title']='Вымышленная экскурсия';
        $data['programs'][0]['source_url']='https://example.org/fake';
        $path=storage_path('framework/testing/forged-excursions.json');
        if (!is_dir(dirname($path))) mkdir(dirname($path),0700,true);
        file_put_contents($path,json_encode($data,JSON_UNESCAPED_UNICODE));
        try{
            $this->assertSame(1,Artisan::call('museum:import-official-excursion-programs',[
                '--source'=>$path,'--apply'=>true,
            ]));
            $this->assertDatabaseCount('museum_entries',0);
        }finally{ @unlink($path); }
    }

    public function test_collision_and_production_import_fail_closed(): void
    {
        $this->seed(ReferenceMuseumSectionsSeeder::class);
        MuseumEntry::create([
            'slug'=>'museum-tour-kolobok', 'type'=>'news', 'title'=>'Unrelated',
            'body'=>'<p>Not an excursion.</p>','status'=>'draft',
        ]);
        $this->assertSame(1,Artisan::call('museum:import-official-excursion-programs',['--apply'=>true]));
        $this->assertDatabaseCount('museum_entries',1);
        $this->assertSame('Unrelated',MuseumEntry::firstOrFail()->title);
        $previous=app()->environment();
        app()->instance('env','production');
        try{
            $this->assertSame(1,Artisan::call('museum:import-official-excursion-programs',['--apply'=>true]));
        }finally{ app()->instance('env',$previous); }
        $this->assertDatabaseCount('museum_entries',1);
    }
}
