<?php

declare(strict_types=1);

namespace App\MoonShine\Resources\MuseumEntry;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Builder;
use MoonShine\Laravel\MoonShineAuth;
use MoonShine\Support\Enums\Ability;
use App\Support\MuseumSectionAccess;
use App\Support\MuseumEntryRevisionGuard;
use App\Support\MuseumEditConflict;
use App\Support\MuseumEditConflictResponse;
use Illuminate\Support\Facades\DB;
use MoonShine\Contracts\Core\TypeCasts\DataWrapperContract;
use MoonShine\Contracts\Core\DependencyInjection\FieldsContract;
use Symfony\Component\HttpFoundation\Response;
use Throwable;
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

    /**
     * Keep the fingerprint check and the actual MoonShine form mutation in
     * ONE database transaction. PostgreSQL/MySQL lockForUpdate serializes
     * editors; SQLite concurrent writes can fail closed with a busy error.
     * A stale browser form may never silently overwrite a newer version.
     */
    public function save(DataWrapperContract $item, ?FieldsContract $fields = null): DataWrapperContract
    {
        return DB::transaction(fn (): DataWrapperContract => parent::save($item, $fields), 3);
    }

    protected function beforeUpdating(DataWrapperContract $item): DataWrapperContract
    {
        // Preserve the stronger 403 for unauthorized cross-section moves
        // even when a forged update omits the editorial revision token.
        $actor = MuseumSectionAccess::user();
        $target = request()->input('museum_section_id');
        if ($actor === null || ! MuseumSectionAccess::mayEdit($actor, $target)) {
            abort(403);
        }
        app(MuseumEntryRevisionGuard::class)->assertCurrent(
            (int) $item->getKey(),
            request()->input('_museum_revision_sha256'),
        );
        return parent::beforeUpdating($item);
    }

    public function modifyErrorResponse(Response $response, Throwable $exception): Response
    {
        // MoonShine catches thrown errors in production, where its default
        // handler redirects and would lose the comparison UX. Only our typed
        // 409 is eligible; 403, CSRF and all other failures remain unchanged.
        if ($exception instanceof MuseumEditConflict) {
            return app(MuseumEditConflictResponse::class)->render(
                request(), (int) $this->getItemID(), $exception
            );
        }
        return parent::modifyErrorResponse($response, $exception);
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
