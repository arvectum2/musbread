<?php

declare(strict_types=1);

namespace App\MoonShine\Resources\MuseumEntry;

use Illuminate\Database\Eloquent\Model;
use App\Models\MuseumEntry;
use App\MoonShine\Resources\MuseumEntry\Pages\MuseumEntryIndexPage;
use App\MoonShine\Resources\MuseumEntry\Pages\MuseumEntryFormPage;
use App\MoonShine\Resources\MuseumEntry\Pages\MuseumEntryDetailPage;

use MoonShine\Laravel\Resources\ModelResource;
use MoonShine\Contracts\Core\PageContract;

/**
 * @extends ModelResource<MuseumEntry, MuseumEntryIndexPage, MuseumEntryFormPage, MuseumEntryDetailPage>
 */
class MuseumEntryResource extends ModelResource
{
    protected string $model = MuseumEntry::class;

    protected string $title = 'Материалы музея';

    /**
     * @return list<class-string<PageContract>>
     */
    protected function pages(): array
    {
        return [
            MuseumEntryIndexPage::class,
            MuseumEntryFormPage::class,
            MuseumEntryDetailPage::class,
        ];
    }
}
