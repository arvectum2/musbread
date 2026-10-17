<?php

declare(strict_types=1);

namespace App\Providers;

use Illuminate\Support\ServiceProvider;
use MoonShine\Contracts\Core\DependencyInjection\CoreContract;
use MoonShine\Laravel\DependencyInjection\MoonShine;
use MoonShine\Laravel\DependencyInjection\MoonShineConfigurator;
use App\MoonShine\Resources\MoonShineUser\MoonShineUserResource;
use App\MoonShine\Resources\MoonShineUserRole\MoonShineUserRoleResource;
use App\MoonShine\Resources\MuseumEvent\MuseumEventResource;
use App\MoonShine\Resources\MuseumEntry\MuseumEntryResource;
use App\MoonShine\Resources\MuseumSection\MuseumSectionResource;
use App\MoonShine\Resources\MuseumFixedPageSeo\MuseumFixedPageSeoResource;
use App\MoonShine\Resources\MuseumVisitorContacts\MuseumVisitorContactsResource;
use App\MoonShine\Resources\MuseumRequest\MuseumRequestResource;
use App\MoonShine\Resources\MuseumRequestTransition\MuseumRequestTransitionResource;
use App\MoonShine\Resources\MuseumAuditRecord\MuseumAuditRecordResource;
use App\MoonShine\Resources\MuseumPublicationRun\MuseumPublicationRunResource;

class MoonShineServiceProvider extends ServiceProvider
{
    /**
     * @param  CoreContract<MoonShineConfigurator>  $core
     */
    public function boot(CoreContract $core): void
    {
        $core
            ->resources([
                MoonShineUserResource::class,
                MoonShineUserRoleResource::class,
                MuseumEventResource::class,
                MuseumEntryResource::class,
                MuseumSectionResource::class,
                MuseumFixedPageSeoResource::class,
                MuseumVisitorContactsResource::class,
                MuseumRequestResource::class,
                MuseumRequestTransitionResource::class,
                MuseumAuditRecordResource::class,
                MuseumPublicationRunResource::class,
            ])
            ->pages([
                ...$core->getConfig()->getPages(),
            ])
        ;
    }
}
