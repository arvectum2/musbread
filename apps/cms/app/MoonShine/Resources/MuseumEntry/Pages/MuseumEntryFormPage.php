<?php

declare(strict_types=1);

namespace App\MoonShine\Resources\MuseumEntry\Pages;

use App\Models\MuseumEntry;
use App\Models\MuseumSection;
use App\Support\MuseumSectionAccess;
use App\Support\MuseumApprovalRevision;
use Illuminate\Validation\Rule;
use MoonShine\Contracts\Core\TypeCasts\DataWrapperContract;
use MoonShine\Laravel\Pages\Crud\FormPage;
use MoonShine\UI\Components\Layout\Box;
use MoonShine\UI\Fields\Date;
use MoonShine\UI\Fields\ID;
use MoonShine\UI\Fields\Hidden;
use MoonShine\UI\Fields\Select;
use MoonShine\UI\Fields\Text;
use MoonShine\UI\Fields\Textarea;
use App\MoonShine\Fields\Jodit;

final class MuseumEntryFormPage extends FormPage
{
    // MoonShine's asynchronous error toast would discard a 409 comparison
    // page. Ordinary POST redirects work here, including Jodit's formdata.
    // The dedicated conflict response preserves submitted values safely.
    protected bool $isAsync = false;

    protected function fields(): iterable
    {
        return [
            Box::make([
                ID::make(),
                self::revisionField(),
                Select::make('Раздел', 'type')
                    ->options(MuseumEntry::TYPES)->required(),
                Text::make('Название', 'title')->required(),
                Text::make('URL (латиница, через дефис)', 'slug')->required(),
                Text::make('H1', 'h1'),
                Select::make('Раздел сайта', 'museum_section_id')
                    ->options(MuseumSection::query()
                        ->whereIn('id', MuseumSectionAccess::user()
                            ? MuseumSectionAccess::allowedIds(MuseumSectionAccess::user()) : [])
                        ->orderBy('sort_order')->pluck('title', 'id')->all())
                    ->nullable(),
                Textarea::make('Анонс', 'excerpt'),
                self::bodyEditorField(),
                // A video is inserted inline with a text paragraph, never
                // arbitrary iframe HTML. Configure its URL, license and
                // textual alternative in the dedicated Video resource.

                Select::make('Статус', 'status')
                    ->options(['draft' => 'Черновик', 'published' => 'Опубликовано'])
                    ->default('draft')->required(),
                Date::make('Публиковать с (дата и время)', 'published_at')->withTime()->nullable(),
                Date::make('Снять с публикации (дата и время)', 'unpublish_at')->withTime()->nullable(),
                Text::make('SEO-заголовок', 'seo_title'),
                Textarea::make('SEO-описание', 'seo_description'),
                Text::make('English title (publish only with English body)', 'title_en'),
                Textarea::make('English excerpt', 'excerpt_en'),
                Textarea::make('English body (safe HTML)', 'body_en'),
                Text::make('English H1', 'h1_en'),
                Text::make('English SEO title', 'seo_title_en'),
                Textarea::make('English SEO description', 'seo_description_en'),
            ]),
        ];
    }

    /** Optimistic-lock value is visible only in the editor's HTML form.
     * Never apply this form-only value to the Eloquent entry.
     */
    private function revisionField(): Hidden
    {
        $item = $this->getResource()->getItemOrInstance();
        $fingerprint = $item instanceof MuseumEntry && $item->exists
            ? MuseumApprovalRevision::fingerprint($item) : '';

        return Hidden::make('Версия открытой редакции', '_museum_revision_sha256')
            ->default($fingerprint)
            ->canApply(static fn (): bool => false);
    }

    /**
     * This is an emergency *source HTML* editor alternative, not WYSIWYG parity.
     * Existing sanitation/publishing rules remain independent of the chosen UI.
     */
    private static function bodyEditorField(): Textarea
    {
        $mode = config('museum.entry_body_editor', 'jodit');

        return match ($mode) {
            'html-source' => Textarea::make('Основной текст (HTML-код; h2, p, ul, li, a)', 'body')
                ->required(),
            'jodit' => Jodit::make('Основной текст (визуальный HTML; видео — [[museum-video:код]])', 'body')->required(),
            default => throw new \InvalidArgumentException(
                'Unsupported museum.entry_body_editor mode; allowed: jodit, html-source'
            ),
        };
    }

    protected function rules(DataWrapperContract $item): array
    {
        return [
            'type' => ['required', Rule::in(array_keys(MuseumEntry::TYPES))],
            'slug' => ['required', 'regex:/^[a-z0-9]+(?:-[a-z0-9]+)*$/', Rule::unique('museum_entries', 'slug')->ignore($item->getKey())],
            'title' => ['required', 'string', 'max:255'],
            'h1' => ['nullable', 'string', 'max:255'],
            'seo_title' => ['nullable', 'string', 'max:255'],
            'seo_description' => ['nullable', 'string', 'max:500'],
            'body' => ['required', 'string'],
            'museum_section_id' => ['nullable', 'integer', Rule::exists('museum_sections', 'id')],
            'status' => ['required', 'in:draft,published'],
            'published_at' => ['nullable', 'date'],
            'unpublish_at' => ['nullable', 'date', 'after:published_at'],
            'title_en' => ['nullable', 'string', 'max:255'],
            'excerpt_en' => ['nullable', 'string'],
            'body_en' => ['nullable', 'string'],
            'h1_en' => ['nullable', 'string', 'max:255'],
            'seo_title_en' => ['nullable', 'string', 'max:255'],
            'seo_description_en' => ['nullable', 'string'],
        ];
    }
}
