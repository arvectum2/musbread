<?php

declare(strict_types=1);

namespace App\MoonShine\Resources\MuseumAuditRecord;

use App\Models\MuseumAuditRecord;
use App\MoonShine\Resources\MuseumAuditRecord\Pages\MuseumAuditRecordIndexPage;
use MoonShine\Contracts\Core\PageContract;
use MoonShine\Laravel\MoonShineAuth;
use MoonShine\Laravel\Resources\ModelResource;
use MoonShine\Support\Enums\Ability;
use MoonShine\Support\Enums\Action;
use MoonShine\Support\ListOf;

/** @extends ModelResource<MuseumAuditRecord, MuseumAuditRecordIndexPage, null, null> */
final class MuseumAuditRecordResource extends ModelResource
{
    protected string $model = MuseumAuditRecord::class;
    protected string $title = 'Журнал изменений';

    protected function pages(): array
    {
        return [MuseumAuditRecordIndexPage::class];
    }

    protected function activeActions(): ListOf
    {
        return parent::activeActions()->except(Action::CREATE, Action::UPDATE, Action::DELETE);
    }

    protected function isCan(Ability $ability): bool
    {
        $user = MoonShineAuth::getGuard()->user();

        return $user !== null
            && $user->isSuperUser()
            && in_array($ability, [Ability::VIEW_ANY, Ability::VIEW], true)
            && parent::isCan($ability);
    }
}
