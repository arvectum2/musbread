<?php

declare(strict_types=1);

namespace App\MoonShine\Resources\MuseumEvent;

use Illuminate\Database\Eloquent\Model;
use App\Models\MuseumEvent;
use App\Support\MuseumSectionAccess;
use MoonShine\Laravel\MoonShineAuth;
use MoonShine\Support\Enums\Ability;
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
    protected function modifyQueryBuilder(\Illuminate\Contracts\Database\Eloquent\Builder $builder): \Illuminate\Contracts\Database\Eloquent\Builder
    {
        $user = MuseumSectionAccess::user();
        return $user === null ? $builder->whereRaw('1=0') : $builder->editableBy($user);
    }

    protected function modifyItemQueryBuilder(\Illuminate\Contracts\Database\Eloquent\Builder $builder): \Illuminate\Contracts\Database\Eloquent\Builder
    {
        return $this->modifyQueryBuilder($builder);
    }

    protected function isCan(Ability $ability): bool
    {
        $user = MoonShineAuth::getGuard()->user();
        if ($user === null) return false;
        if (! $user->isSuperUser()) {
            if ($ability === Ability::CREATE && MuseumSectionAccess::allowedIds($user) === []) return false;
            if ($ability === Ability::MASS_DELETE) return false;
        }
        return parent::isCan($ability);
    }

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
