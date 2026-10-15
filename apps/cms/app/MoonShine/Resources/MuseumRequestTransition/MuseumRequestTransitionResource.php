<?php

declare(strict_types=1);

namespace App\MoonShine\Resources\MuseumRequestTransition;

use App\Models\MuseumRequestTransition;
use App\MoonShine\Resources\MuseumRequestTransition\Pages\MuseumRequestTransitionIndexPage;
use MoonShine\Laravel\Resources\ModelResource;
use MoonShine\Laravel\MoonShineAuth;
use MoonShine\Support\Enums\Ability;
use MoonShine\Support\Enums\Action;
use MoonShine\Support\ListOf;

final class MuseumRequestTransitionResource extends ModelResource
{
    protected string $model = MuseumRequestTransition::class;
    protected string $title = 'История статусов обращений';

    protected function pages(): array
    {
        return [MuseumRequestTransitionIndexPage::class];
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
