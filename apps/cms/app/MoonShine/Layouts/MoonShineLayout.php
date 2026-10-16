<?php

declare(strict_types=1);

namespace App\MoonShine\Layouts;

use MoonShine\Laravel\Layouts\AppLayout;
use MoonShine\ColorManager\Palettes\PurplePalette;
use MoonShine\ColorManager\ColorManager;
use MoonShine\Contracts\ColorManager\ColorManagerContract;
use MoonShine\Contracts\ColorManager\PaletteContract;
use App\MoonShine\Resources\MuseumEvent\MuseumEventResource;
use MoonShine\MenuManager\MenuItem;
use App\MoonShine\Resources\MuseumEntry\MuseumEntryResource;
use App\MoonShine\Resources\MuseumSection\MuseumSectionResource;
use App\MoonShine\Resources\MuseumRequest\MuseumRequestResource;
use App\MoonShine\Resources\MuseumRequestTransition\MuseumRequestTransitionResource;
use App\MoonShine\Resources\MuseumAuditRecord\MuseumAuditRecordResource;
use App\MoonShine\Resources\MuseumPublicationRun\MuseumPublicationRunResource;
use MoonShine\Laravel\MoonShineAuth;

final class MoonShineLayout extends AppLayout
{
    /**
     * @var null|class-string<PaletteContract>
     */
    protected ?string $palette = PurplePalette::class;

    protected function assets(): array
    {
        return [
            ...parent::assets(),
        ];
    }

    protected function menu(): array
    {
        return [
            ...parent::menu(),
            MenuItem::make(MuseumEventResource::class, 'События'),
            MenuItem::make(MuseumEntryResource::class, 'Материалы музея'),
            MenuItem::make(MuseumSectionResource::class, 'Структура сайта'),
            MenuItem::make(MuseumRequestResource::class, 'Обращения (демо)'),
            MenuItem::make(MuseumRequestTransitionResource::class, 'История обращений'),
            MenuItem::make('/admin/museum-media', 'Медиатека'),
            MenuItem::make(MuseumAuditRecordResource::class, 'Журнал изменений'),
            ...(MoonShineAuth::getGuard()->user()?->isSuperUser() ? [MenuItem::make('/admin/museum-activity', 'Статистика действий')] : []),
            MenuItem::make(MuseumPublicationRunResource::class, 'Публикации'),
        ];
    }

    /**
     * @param ColorManager $colorManager
     */
    protected function colors(ColorManagerContract $colorManager): void
    {
        parent::colors($colorManager);

        // $colorManager->primary('#00000');
    }
}
