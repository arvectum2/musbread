<?php

namespace App\Support;

use App\Models\MuseumSection;
use MoonShine\Laravel\Models\MoonshineUser;
use MoonShine\Laravel\MoonShineAuth;

/** Default-deny section grants for MoonShine editorial users. */
final class MuseumSectionAccess
{
    public static function user(): ?MoonshineUser
    {
        $user = MoonShineAuth::getGuard()->user();
        return $user instanceof MoonshineUser ? $user : null;
    }

    public static function mayEdit(?MoonshineUser $user, ?int $sectionId): bool
    {
        if ($user === null) return false;
        if ($user->isSuperUser()) return true;
        if ($sectionId === null) return false;
        return MuseumSection::query()->whereKey($sectionId)
            ->whereHas('editors', fn ($query) => $query->whereKey($user->getKey()))
            ->exists();
    }

    public static function allowedIds(MoonshineUser $user): array
    {
        if ($user->isSuperUser()) {
            return MuseumSection::query()->pluck('id')->all();
        }
        return MuseumSection::query()->whereHas(
            'editors',
            fn ($query) => $query->whereKey($user->getKey())
        )->pluck('id')->all();
    }
}
