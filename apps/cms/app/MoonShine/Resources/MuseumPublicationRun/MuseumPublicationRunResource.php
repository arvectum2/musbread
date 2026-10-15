<?php

declare(strict_types=1);

namespace App\MoonShine\Resources\MuseumPublicationRun;

use App\Models\MuseumPublicationRun;
use App\MoonShine\Resources\MuseumPublicationRun\Pages\MuseumPublicationRunIndexPage;
use MoonShine\Laravel\MoonShineAuth;
use MoonShine\Laravel\Resources\ModelResource;
use MoonShine\Support\Enums\Ability;
use MoonShine\Support\Enums\Action;
use MoonShine\Support\ListOf;

/** @extends ModelResource<MuseumPublicationRun, MuseumPublicationRunIndexPage, null, null> */
final class MuseumPublicationRunResource extends ModelResource
{
    protected string $model = MuseumPublicationRun::class;
    protected string $title = 'Запуски публикации';

    protected function pages(): array
    {
        return [MuseumPublicationRunIndexPage::class];
    }

    protected function activeActions(): ListOf
    {
        return parent::activeActions()->except(Action::CREATE, Action::UPDATE, Action::DELETE);
    }

    protected function isCan(Ability $ability): bool
    {
        $user = MoonShineAuth::getGuard()->user();
        return $user !== null && $user->isSuperUser()
            && in_array($ability, [Ability::VIEW_ANY, Ability::VIEW], true)
            && parent::isCan($ability);
    }
}
