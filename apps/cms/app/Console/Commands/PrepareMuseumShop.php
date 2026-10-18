<?php

namespace App\Console\Commands;

use App\Models\MuseumEntry;
use App\Models\MuseumSection;
use Illuminate\Console\Command;
use RuntimeException;
use Throwable;

/**
 * TZ-145: existing CMS section plus an editable EMPTY storefront introduction.
 * Never seeds fake merchandise, SKUs, stock, prices or external checkout URLs.
 */
final class PrepareMuseumShop extends Command
{
    protected $signature = 'museum:prepare-shop
        {--apply : Create one private editorial introduction in existing museum-shop section}';

    protected $description = 'Prepare source-honest noncommerce souvenir shop placeholder for museum editor';

    public function handle(): int
    {
        if ($this->option('apply') && app()->environment('production')) {
            $this->error('Shop creation in production requires reviewed MoonShine editorial workflow.');
            return self::FAILURE;
        }
        try {
            $section = MuseumSection::where('slug','museum-shop')->first();
            if (! $section || $section->parent?->slug !== 'visitors'
                || $section->legacy_path !== null) {
                throw new RuntimeException('TZ-145 shop section missing or incorrectly mapped.');
            }
            $other = MuseumEntry::where('slug','museum-shop')->first();
            if ($other && ($other->type !== 'page' || $other->museum_section_id !== $section->id)) {
                throw new RuntimeException('CMS shop slug already belongs to unrelated content.');
            }
            $this->info(($other ? 'KEEP EDITOR' : 'NEW PRIVATE DRAFT').' museum-shop');
            if (! $this->option('apply')) {
                $this->info('Dry run: no changes, no merchandise created.');
                return self::SUCCESS;
            }
            MuseumEntry::firstOrCreate(['slug'=>'museum-shop'],[
                'museum_section_id'=>$section->id,
                'type'=>'page',
                'title'=>'Магазин музея',
                'h1'=>'Магазин музея',
                'excerpt'=>'Информационная витрина без продажи. Ассортимент уточняется у музея.',
                'body'=>'<p>Информационная витрина музея: без корзины, оплаты и оформления заказов. '
                    .'После передачи музейной номенклатуры редактор сможет добавить '
                    .'отдельные подтверждённые описания сувениров в этот раздел.</p>',
                'status'=>'draft',
                'published_at'=>null,
            ]);
            $this->info('Private editor-ready shop landing page created; zero mock products or commerce functions.');
            return self::SUCCESS;
        } catch (Throwable $e) {
            $this->error('Cannot prepare museum shop: '.$e->getMessage());
            return self::FAILURE;
        }
    }
}
