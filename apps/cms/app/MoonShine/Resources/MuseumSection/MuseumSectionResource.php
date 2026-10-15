<?php

declare(strict_types=1);

namespace App\MoonShine\Resources\MuseumSection;

use App\Models\MuseumSection;
use App\MoonShine\Resources\MuseumSection\Pages\MuseumSectionFormPage;
use App\MoonShine\Resources\MuseumSection\Pages\MuseumSectionIndexPage;
use MoonShine\Contracts\Core\PageContract;
use MoonShine\Laravel\MoonShineAuth;
use MoonShine\Laravel\Resources\ModelResource;
use MoonShine\Support\Enums\Ability;

/** Parent/child structural management is exclusively for superusers. */
class MuseumSectionResource extends ModelResource
{
    protected string $model = MuseumSection::class;
    protected string $title = 'Структура сайта';

    protected function isCan(Ability $ability): bool
    {
        $user = MoonShineAuth::getGuard()->user();
        return $user !== null && $user->isSuperUser() && parent::isCan($ability);
    }

    /** @return list<class-string<PageContract>> */
    protected function pages(): array
    {
        return [MuseumSectionIndexPage::class, MuseumSectionFormPage::class];
    }
}
