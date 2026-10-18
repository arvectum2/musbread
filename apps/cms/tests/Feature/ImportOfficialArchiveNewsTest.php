<?php

declare(strict_types=1);

namespace Tests\Feature;

use App\Models\MuseumEntry;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Artisan;
use Tests\TestCase;

final class ImportOfficialArchiveNewsTest extends TestCase
{
    use RefreshDatabase;

    public function test_twenty_archival_news_are_private_idempotent_and_not_events():void
    {
        $this->assertSame(0,Artisan::call('museum:import-official-archive-news'),Artisan::output());
        $this->assertDatabaseCount('museum_entries',0);
        $this->assertSame(0,Artisan::call('museum:import-official-archive-news',[
            '--apply'=>true,
        ]),Artisan::output());
        $this->assertSame(20,MuseumEntry::where('type','news')->where('status','draft')->count());
        $this->assertSame(0,MuseumEntry::where('status','published')->count());
        $this->assertDatabaseCount('museum_events',0);
        $this->assertDatabaseCount('museum_media',0);
        $this->assertSame(0,Artisan::call('museum:import-official-archive-news',[
            '--apply'=>true,
        ]),Artisan::output());
        $this->assertDatabaseCount('museum_entries',20);
    }

    public function test_editorial_edits_are_preserved_on_reimport():void
    {
        $source=json_decode((string)file_get_contents(
            base_path('../web/src/data/official-museum-news-archive.json')),true);
        $slug=$source['articles'][0]['slug'];
        MuseumEntry::create([
            'slug'=>$slug,'type'=>'news','status'=>'draft',
            'title'=>'Редакторская правка архива',
            'body'=>'<p>Текст редакции, сохранённый музеем.</p>',
        ]);
        $this->assertSame(0,Artisan::call('museum:import-official-archive-news',[
            '--apply'=>true,
        ]),Artisan::output());
        $this->assertSame('Редакторская правка архива',MuseumEntry::where('slug',$slug)->firstOrFail()->title);
        $this->assertSame(20,MuseumEntry::where('type','news')->count());
    }

    public function test_tampered_archive_text_is_rejected_atomically():void
    {
        $source=json_decode((string)file_get_contents(
            base_path('../web/src/data/official-museum-news-archive.json')),true);
        $source['articles'][0]['html'].='<script>bad()</script>';
        $path=storage_path('framework/testing/tampered-museum-news-archive.json');
        try {
            file_put_contents($path,json_encode($source,JSON_UNESCAPED_UNICODE));
            $this->assertSame(1,Artisan::call('museum:import-official-archive-news',[
                '--apply'=>true,'--source'=>$path,
            ]));
            $this->assertDatabaseCount('museum_entries',0);
        } finally {
            @unlink($path);
        }
    }
}
