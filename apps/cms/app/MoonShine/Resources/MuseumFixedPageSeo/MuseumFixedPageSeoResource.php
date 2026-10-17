<?php

declare(strict_types=1);

namespace App\MoonShine\Resources\MuseumFixedPageSeo;

use App\Models\MuseumFixedPageSeo;
use App\MoonShine\Resources\MuseumFixedPageSeo\Pages\FixedPageSeoIndexPage;
use App\MoonShine\Resources\MuseumFixedPageSeo\Pages\FixedPageSeoFormPage;
use MoonShine\Contracts\Core\PageContract;
use MoonShine\Laravel\MoonShineAuth;
use MoonShine\Laravel\Resources\ModelResource;
use MoonShine\Support\Enums\Ability;

final class MuseumFixedPageSeoResource extends ModelResource
{
    protected string $model = MuseumFixedPageSeo::class;
    protected string $title = 'SEO фиксированных страниц';

    protected function isCan(Ability $ability): bool
    {
        $user = MoonShineAuth::getGuard()->user();
        return $user !== null && $user->isSuperUser() && parent::isCan($ability);
    }

    /** @return list<class-string<PageContract>> */
    protected function pages(): array
    {
        return [FixedPageSeoIndexPage::class, FixedPageSeoFormPage::class];
    }
}
