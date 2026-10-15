<?php

declare(strict_types=1);

namespace App\MoonShine\Resources\MuseumRequest;

use App\Models\MuseumRequest;
use App\Support\MuseumSectionAccess;
use App\MoonShine\Resources\MuseumRequest\Pages\MuseumRequestIndexPage;
use App\MoonShine\Resources\MuseumRequest\Pages\MuseumRequestFormPage;
use Illuminate\Contracts\Database\Eloquent\Builder;
use MoonShine\Contracts\Core\PageContract;
use MoonShine\Laravel\Resources\ModelResource;
use MoonShine\Support\Enums\Ability;
use MoonShine\Support\Enums\Action;
use MoonShine\Support\ListOf;

/**
 * Staff-only synthetic case tracker. No public-facing request API or PII fields.
 */
class MuseumRequestResource extends ModelResource
{
    protected string $model = MuseumRequest::class;
    protected string $title = 'Обращения и экскурсии (демо)';

    protected function modifyQueryBuilder(Builder $builder): Builder
    {
        $user = MuseumSectionAccess::user();
        return $user === null ? $builder->whereRaw('1=0') : $builder->visibleTo($user);
    }

    protected function modifyItemQueryBuilder(Builder $builder): Builder
    {
        return $this->modifyQueryBuilder($builder);
    }

    protected function isCan(Ability $ability): bool
    {
        $user = MuseumSectionAccess::user();
        if ($user === null || in_array($ability, [Ability::DELETE, Ability::MASS_DELETE], true)) {
            return false;
        }
        if ($ability === Ability::CREATE && ! $user->isSuperUser()) {
            return false;
        }
        return parent::isCan($ability);
    }

    protected function activeActions(): ListOf
    {
        return parent::activeActions()->except(Action::DELETE);
    }

    /** @return list<class-string<PageContract>> */
    protected function pages(): array
    {
        return [MuseumRequestIndexPage::class, MuseumRequestFormPage::class];
    }
}
