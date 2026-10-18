<?php

declare(strict_types=1);

namespace Tests\Feature;

use App\Models\MuseumEntry;
use Database\Seeders\ReferenceMuseumSectionsSeeder;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Artisan;
use Tests\TestCase;

final class PrepareMuseumShopTest extends TestCase
{
    use RefreshDatabase;

    public function test_opt_in_shop_page_is_private_empty_and_noncommercial():void
    {
        $this->seed(ReferenceMuseumSectionsSeeder::class);
        $this->assertSame(0,Artisan::call('museum:prepare-shop'));
        $this->assertDatabaseCount('museum_entries',0);
        $this->assertSame(0,Artisan::call('museum:prepare-shop',['--apply'=>true]));
        $this->assertDatabaseCount('museum_entries',1);
        $entry=MuseumEntry::where('slug','museum-shop')->firstOrFail();
        $this->assertSame('page',$entry->type);
        $this->assertSame('draft',$entry->status);
        $this->assertNull($entry->published_at);
        $this->assertSame('museum-shop',$entry->section->slug);
        $this->assertSame(0,$entry->documents()->count());
        $this->assertSame(0,$entry->media()->count());
        $this->assertStringContainsString('без корзины',$entry->body);
        $this->assertStringNotContainsString('999 рублей',$entry->body);
        $entry->update(['body'=>'<p>Редактор добавил описание витрины.</p>']);
        $this->assertSame(0,Artisan::call('museum:prepare-shop',['--apply'=>true]));
        $this->assertDatabaseCount('museum_entries',1);
        $this->assertSame('<p>Редактор добавил описание витрины.</p>',$entry->fresh()->body);
    }

    public function test_shop_slug_collision_does_not_overwrite_other_author():void
    {
        $this->seed(ReferenceMuseumSectionsSeeder::class);
        MuseumEntry::create(['slug'=>'museum-shop','type'=>'news','title'=>'Чужой материал',
            'status'=>'draft','body'=>'<p>Не витрина.</p>']);
        $this->assertSame(1,Artisan::call('museum:prepare-shop',['--apply'=>true]));
        $this->assertDatabaseCount('museum_entries',1);
        $this->assertSame('Чужой материал',MuseumEntry::firstOrFail()->title);
    }

    public function test_no_production_bulk_shop_seed():void
    {
        $old=app()->environment();
        app()->instance('env','production');
        try{
            $this->assertSame(1,Artisan::call('museum:prepare-shop',['--apply'=>true]));
        }finally{app()->instance('env',$old);}
    }
}
