<?php
declare(strict_types=1);
namespace App\MoonShine\Resources\MuseumInboundRequest;
use App\Models\MuseumInboundRequest;
use App\MoonShine\Resources\MuseumInboundRequest\Pages\InboxIndexPage;
use App\MoonShine\Resources\MuseumInboundRequest\Pages\InboxDetailPage;
use MoonShine\Laravel\MoonShineAuth;
use MoonShine\Laravel\Resources\ModelResource;
use MoonShine\Support\Enums\Ability;
use MoonShine\Support\Enums\Action;
use MoonShine\Support\ListOf;
final class MuseumInboundRequestResource extends ModelResource {
    protected string $model=MuseumInboundRequest::class;
    protected string $title='Обращения посетителей';
    protected function pages(): array {return [InboxIndexPage::class,InboxDetailPage::class];}
    protected function activeActions(): ListOf {
        return parent::activeActions()->except(Action::CREATE,Action::UPDATE,Action::DELETE);
    }
    protected function isCan(Ability $ability): bool {
        $user=MoonShineAuth::getGuard()->user();
        return $user!==null && $user->isSuperUser()
            && in_array($ability,[Ability::VIEW_ANY,Ability::VIEW],true)
            && parent::isCan($ability);
    }
}
