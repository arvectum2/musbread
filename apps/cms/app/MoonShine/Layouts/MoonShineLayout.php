<?php

declare(strict_types=1);

namespace App\MoonShine\Layouts;

use MoonShine\Laravel\Layouts\AppLayout;
use MoonShine\AssetManager\Css;
use MoonShine\AssetManager\Js;
use MoonShine\ColorManager\Palettes\PurplePalette;
use MoonShine\ColorManager\ColorManager;
use MoonShine\Contracts\ColorManager\ColorManagerContract;
use MoonShine\Contracts\ColorManager\PaletteContract;
use App\MoonShine\Resources\MuseumEvent\MuseumEventResource;
use MoonShine\MenuManager\MenuItem;
use App\MoonShine\Resources\MuseumEntry\MuseumEntryResource;
use App\MoonShine\Resources\MuseumSection\MuseumSectionResource;
use App\MoonShine\Resources\MuseumFixedPageSeo\MuseumFixedPageSeoResource;
use App\MoonShine\Resources\MuseumVisitorContacts\MuseumVisitorContactsResource;
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
            Css::make('/css/museum-cms-accessibility.css'),
            Js::make('/js/museum-cms-accessibility.js')->defer(),
        ];
    }

    protected function menu(): array
    {
        $admin = MoonShineAuth::getGuard()->user()?->isSuperUser() ?? false;
        // The daily editorial task comes first. Technical resources and
        // demo-only workflows are still registered, but never clutter the
        // standard editor navigation or advertise inaccessible resources.
        return [
            ...parent::menu(),
            MenuItem::make(MuseumEntryResource::class, 'Материалы и новости'),
            MenuItem::make(MuseumEventResource::class, 'Афиша и мероприятия'),
            MenuItem::make('/admin/museum-media', 'Изображения'),
            MenuItem::make('/admin/museum-documents', 'Документы'),
            MenuItem::make('/admin/museum-content/preflight', 'Проверить перед публикацией'),
            MenuItem::make('/admin/museum-content/links', 'Подобрать ссылку в текст'),
            ...($admin ? [
                MenuItem::make(MuseumSectionResource::class, 'Структура сайта'),
                MenuItem::make(MuseumFixedPageSeoResource::class, 'SEO фиксированных страниц'),
                MenuItem::make(MuseumVisitorContactsResource::class, 'Контакты и часы работы'),
                MenuItem::make('/admin/museum-sections/tree', 'Карта разделов'),
                MenuItem::make('/admin/museum-content/compare', 'Сравнить версии'),
                MenuItem::make('/admin/museum-content/review-notes', 'Согласование материалов'),
                // Demonstration requests are not a live museum inbox.
                MenuItem::make(MuseumRequestResource::class, 'Обращения (демо)'),
                MenuItem::make(MuseumRequestTransitionResource::class, 'История обращений'),
                MenuItem::make(MuseumAuditRecordResource::class, 'Журнал изменений'),
                MenuItem::make('/admin/museum-activity', 'Статистика действий'),
                MenuItem::make(MuseumPublicationRunResource::class, 'Запуски публикации'),
            ] : []),
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
