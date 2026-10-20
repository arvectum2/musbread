<?php

declare(strict_types=1);

namespace App\Support;

use App\Models\MuseumEntry;
use Illuminate\Http\Request;
use Symfony\Component\HttpFoundation\Response;

/**
 * Never store a submitted, stale HTML draft in DB, logs, or flashed session.
 * Reflect it only to the authenticated editor who attempted the save, with
 * strict escaped HTML, no-store headers, and no external requests.
 */
final class MuseumEditConflictResponse
{
    private const LABELS = [
        'title' => 'Название',
        'slug' => 'Адрес страницы',
        'h1' => 'Заголовок H1',
        'excerpt' => 'Анонс',
        'body' => 'Основной текст (HTML)',
        'status' => 'Статус',
        'published_at' => 'Публиковать с',
        'unpublish_at' => 'Снять с публикации',
        'seo_title' => 'SEO-заголовок',
        'seo_description' => 'SEO-описание',
        'title_en' => 'English title',
        'excerpt_en' => 'English excerpt',
        'body_en' => 'English body',
        'h1_en' => 'English H1',
        'seo_title_en' => 'English SEO title',
        'seo_description_en' => 'English SEO description',
    ];

    public function render(Request $request, int $entryId, MuseumEditConflict $conflict): Response
    {
        $editor = MuseumSectionAccess::user();
        abort_if($editor === null, 403);
        $entry = MuseumEntry::query()->editableBy($editor)->findOrFail($entryId);

        // Recheck current authorization before exposing the latest text or
        // showing a stale submitted draft. Never use user-supplied record ID.
        abort_unless(
            MuseumSectionAccess::mayEdit($editor, $entry->museum_section_id),
            403
        );

        $fields = [];
        foreach (self::LABELS as $key => $label) {
            $submitted = $request->input($key);
            $current = $entry->getAttribute($key);
            if (! is_scalar($submitted) && $submitted !== null) {
                $submitted = '';
            }
            $currentValue = $current instanceof \DateTimeInterface
                ? $current->format('Y-m-d H:i:s')
                : (is_scalar($current) ? (string) $current : '');
            $editedValue = $submitted === null ? '' : (string) $submitted;
            $fields[] = [
                'key' => $key,
                'label' => $label,
                'submitted' => $editedValue,
                'current' => $currentValue,
                'different' => $editedValue !== $currentValue,
            ];
        }

        $prefix = trim((string) config('moonshine.prefix', 'admin'), '/');
        $editorUrl = url('/'.$prefix.'/resource/museum-entry-resource/museum-entry-form-page/'.$entry->getKey());

        return response()->view('entries.edit-conflict', [
            'entry' => $entry,
            'fields' => $fields,
            'editorUrl' => $editorUrl,
            'explanation' => $conflict->getMessage(),
        ], 409, [
            'Cache-Control' => 'private, no-store, max-age=0',
            'Pragma' => 'no-cache',
            'X-Content-Type-Options' => 'nosniff',
            'Referrer-Policy' => 'no-referrer',
            'X-Robots-Tag' => 'noindex, noarchive',
            'Content-Security-Policy' => "default-src 'none'; script-src 'self'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'",
        ]);
    }
}
