<?php
declare(strict_types=1);

namespace App\MoonShine\Resources\MuseumVideo;

use App\Models\MuseumVideo;
use App\Support\MuseumSectionAccess;
use App\MoonShine\Resources\MuseumVideo\Pages\MuseumVideoIndexPage;
use App\MoonShine\Resources\MuseumVideo\Pages\MuseumVideoFormPage;
use Illuminate\Contracts\Database\Eloquent\Builder;
use MoonShine\Laravel\MoonShineAuth;
use MoonShine\Laravel\Resources\ModelResource;
use MoonShine\Support\Enums\Ability;
use MoonShine\Contracts\Core\PageContract;

final class MuseumVideoResource extends ModelResource {
    protected string $model=MuseumVideo::class;
    protected string $title='Видео материалов (проверенные VK-ссылки)';
    protected function modifyQueryBuilder(Builder $builder):Builder {
        $user=MuseumSectionAccess::user();
        return $user===null?$builder->whereRaw('1=0'):$builder->whereHas(
            'entry',static fn($q)=>$q->editableBy($user));
    }
    protected function modifyItemQueryBuilder(Builder $builder):Builder {
        return $this->modifyQueryBuilder($builder);
    }
    protected function isCan(Ability $ability):bool {
        $user=MoonShineAuth::getGuard()->user();
        if(!$user)return false;
        if(!$user->isSuperUser()&&
           ($ability===Ability::MASS_DELETE
            ||$ability===Ability::CREATE && MuseumSectionAccess::allowedIds($user)===[]))
           return false;
        return parent::isCan($ability);
    }
    protected function search():array{return ['title','code'];}
    /** @return list<class-string<PageContract>> */
    protected function pages():array{
        return [MuseumVideoIndexPage::class,MuseumVideoFormPage::class];
    }
}
