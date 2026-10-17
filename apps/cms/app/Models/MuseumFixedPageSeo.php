<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Validation\ValidationException;

/**
 * Admin-only SEO overrides for FIXED public routes. CMS entry/event URLs
 * retain their existing original SEO forms; no duplicate canonical owner.
 */
final class MuseumFixedPageSeo extends Model
{
    protected $table = 'museum_fixed_page_seo';

    protected $fillable = ['path', 'seo_title', 'seo_description', 'h1', 'status'];

    public static function validFixedPath(string $value): bool
    {
        if (in_array($value, [
            '/', '/museum/', '/news/', '/excursions/',
            '/exhibitions/', '/documents/', '/search/', '/events/',
        ], true)) return true;

        return preg_match('#^/guide/[a-z0-9]+(?:-[a-z0-9]+)*/$#D', $value) === 1;
    }

    protected static function booted(): void
    {
        static::saving(static function (self $page): void {
            if (! self::validFixedPath((string) $page->path)) {
                throw ValidationException::withMessages([
                    'path' => 'Допустимы только фиксированные страницы сайта и /guide/{slug}/. Для материала/события используйте его карточку.',
                ]);
            }
            if (! in_array($page->status, ['draft', 'published'], true)) {
                throw ValidationException::withMessages(['status' => 'Недопустимый статус SEO страницы.']);
            }
        });
    }
}
