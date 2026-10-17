<?php

declare(strict_types=1);

namespace App\MoonShine\Resources\MuseumEntry;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Builder;
use MoonShine\Laravel\MoonShineAuth;
use MoonShine\Support\Enums\Ability;
use App\Support\MuseumSectionAccess;
use App\Models\MuseumEntry;
use App\MoonShine\Resources\MuseumEntry\Pages\MuseumEntryIndexPage;
use App\MoonShine\Resources\MuseumEntry\Pages\MuseumEntryFormPage;
use App\MoonShine\Resources\MuseumEntry\Pages\MuseumEntryDetailPage;

use MoonShine\Laravel\Resources\ModelResource;
use MoonShine\Contracts\Core\PageContract;

/**
 * @extends ModelResource<MuseumEntry, MuseumEntryIndexPage, MuseumEntryFormPage, MuseumEntryDetailPage>
 */
class MuseumEntryResource extends ModelResource
{
    protected function modifyQueryBuilder(\Illuminate\Contracts\Database\Eloquent\Builder $builder): \Illuminate\Contracts\Database\Eloquent\Builder
    {
        $user = MuseumSectionAccess::user();
        if ($user === null) return $builder->whereRaw('1=0');
        return $builder->editableBy($user)
            ->with('section:id,title')
            ->withCount([
                'relatedEntries as editorial_related_entries_count' => static fn ($q) => $q->editableBy($user),
                'linkedEvents as editorial_linked_events_count' => static fn ($q) => $q->editableBy($user),
            ]);
    }

    protected function modifyItemQueryBuilder(\Illuminate\Contracts\Database\Eloquent\Builder $builder): \Illuminate\Contracts\Database\Eloquent\Builder
    {
        $user = MuseumSectionAccess::user();
        return $user === null ? $builder->whereRaw('1=0') : $builder->editableBy($user);
    }

    protected function isCan(Ability $ability): bool
    {
        $user = MoonShineAuth::getGuard()->user();
        if ($user === null) return false;
        if (! $user->isSuperUser()) {
            if ($ability === Ability::CREATE) {
                if (count(MuseumSectionAccess::allowedIds($user)) === 0) return false;
            } elseif ($ability === Ability::MASS_DELETE) {
                return false;
            }
        }
        return parent::isCan($ability);
    }

    protected function search(): array
    {
        return ['title', 'slug', 'h1'];
    }

    protected string $model = MuseumEntry::class;

    protected string $title = 'Материалы музея';

    /**
     * @return list<class-string<PageContract>>
     */
    protected function pages(): array
    {
        return [
            MuseumEntryIndexPage::class,
            MuseumEntryFormPage::class,
            MuseumEntryDetailPage::class,
        ];
    }
}
