<?php
declare(strict_types=1);
namespace App\MoonShine\Resources\MuseumVisitorContacts;
use App\Models\MuseumVisitorContacts;
use App\MoonShine\Resources\MuseumVisitorContacts\Pages\VisitorContactsIndexPage;
use App\MoonShine\Resources\MuseumVisitorContacts\Pages\VisitorContactsFormPage;
use MoonShine\Contracts\Core\PageContract;
use MoonShine\Laravel\MoonShineAuth;
use MoonShine\Laravel\Resources\ModelResource;
use MoonShine\Support\Enums\Ability;

final class MuseumVisitorContactsResource extends ModelResource {
    protected string $model=MuseumVisitorContacts::class;
    protected string $title='Контакты и часы работы';
    protected function isCan(Ability $ability):bool {
        $user=MoonShineAuth::getGuard()->user();
        return $user!==null && $user->isSuperUser() && parent::isCan($ability);
    }
    /** @return list<class-string<PageContract>> */
    protected function pages():array {
        return [VisitorContactsIndexPage::class,VisitorContactsFormPage::class];
    }
}
