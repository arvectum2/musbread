<?php

declare(strict_types=1);

namespace App\MoonShine\Resources\MuseumEvent;

use Illuminate\Database\Eloquent\Model;
use App\Models\MuseumEvent;
use App\MoonShine\Resources\MuseumEvent\Pages\MuseumEventIndexPage;
use App\MoonShine\Resources\MuseumEvent\Pages\MuseumEventFormPage;
use App\MoonShine\Resources\MuseumEvent\Pages\MuseumEventDetailPage;

use MoonShine\Laravel\Resources\ModelResource;
use MoonShine\Contracts\Core\PageContract;

/**
 * @extends ModelResource<MuseumEvent, MuseumEventIndexPage, MuseumEventFormPage, MuseumEventDetailPage>
 */
class MuseumEventResource extends ModelResource
{
    protected string $model = MuseumEvent::class;

    protected string $title = 'События';

    /**
     * @return list<class-string<PageContract>>
     */
    protected function pages(): array
    {
        return [
            MuseumEventIndexPage::class,
            MuseumEventFormPage::class,
            MuseumEventDetailPage::class,
        ];
    }
}
