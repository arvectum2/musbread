<?php

namespace App\Http\Controllers;

use App\Models\MuseumEntry;
use App\Models\MuseumMedia;
use App\Support\MuseumSectionAccess;
use App\Support\MuseumSvgRasterizer;
use App\Support\MuseumGifProcessor;
use App\Support\MuseumAltDraft;
use App\Support\MuseumAltPolicy;
use App\Support\MuseumWorkflowEntry;
use Illuminate\Http\JsonResponse;
use Illuminate\Auth\Access\AuthorizationException;
use Illuminate\Http\RedirectResponse;
use Illuminate\Http\Request;
use Illuminate\Http\Response;
use Illuminate\Support\Facades\Storage;
use Illuminate\Support\Str;
use Illuminate\Validation\ValidationException;
use MoonShine\Laravel\MoonShineAuth;

final class MuseumMediaController extends Controller
{
    private function requireEntry(MuseumEntry $entry): void
    {
        if (! MuseumSectionAccess::mayEdit(MuseumSectionAccess::user(), $entry->museum_section_id)) {
            throw new AuthorizationException('Нет доступа к медиатеке этого раздела.');
        }
    }

    public function index(Request $request, MuseumWorkflowEntry $context): \Illuminate\Contracts\View\View
    {
        $user = MuseumSectionAccess::user();
        if ($user === null) throw new AuthorizationException();
        $selectedEntry = $context->selected($request, $user);
        $entries = MuseumEntry::query()->editableBy($user)
            ->orderBy('title')->get(['id', 'title', 'slug', 'status']);
        $query = MuseumMedia::query()->with('entry:id,title,status')
            ->whereIn('museum_entry_id', $entries->pluck('id'));
        if ($selectedEntry !== null) {
            $query->where('museum_entry_id', $selectedEntry->id);
        }
        return view('media.index', [
            'entries' => $entries,
            'selectedEntry' => $selectedEntry,
            'media' => $query->latest()->paginate(30)->withQueryString(),
        ]);
    }

    /** Suggest text from a human caption. Nothing is saved or published here. */
    public function suggestAlt(Request $request, MuseumAltDraft $draft): JsonResponse
    {
        $validated = $request->validate([
            'museum_entry_id' => ['required', 'integer', 'exists:museum_entries,id'],
            'caption' => ['required', 'string', 'min:12', 'max:255'],
        ]);
        $entry = MuseumEntry::findOrFail($validated['museum_entry_id']);
        $this->requireEntry($entry);
        return response()->json([
            'suggestion' => $draft->suggest($validated['caption']),
            'review_required' => true,
            'disclaimer' => 'Предложение основано только на подписи; проверьте соответствие изображению.',
        ])->header('Cache-Control', 'private, no-store')->header('X-Content-Type-Options', 'nosniff');
    }

    public function store(Request $request, MuseumSvgRasterizer $svgRasterizer, MuseumGifProcessor $gifProcessor,
        MuseumWorkflowEntry $context): RedirectResponse
    {
        $validated = $request->validate([
            'museum_entry_id' => ['required', 'integer', 'exists:museum_entries,id'],
            'alt' => ['required', 'string', 'min:3', 'max:'.MuseumAltPolicy::MAX_LENGTH,
                static function (string $field, mixed $value, \Closure $fail): void {
                    if ($issue = MuseumAltPolicy::issue(is_string($value) ? $value : null)) $fail($issue);
                }],
            'long_description' => ['nullable', 'string', 'max:3000'],
            'caption' => ['nullable', 'string', 'max:255'],
            'image' => ['required', 'file', 'max:5120'],
        ], [
            'museum_entry_id.required' => 'Выберите материал, к которому относится изображение.',
            'museum_entry_id.exists' => 'Материал не найден: откройте актуальную карточку.',
            'alt.required' => 'Опишите, что видно на изображении, прежде чем загружать файл.',
            'alt.min' => 'Описание слишком короткое: не менее :min символов.',
            'alt.max' => 'Описание слишком длинное: не более :max символов.',
            'image.required' => 'Выберите изображение для загрузки.',
            'image.file' => 'Выберите файл изображения в поддерживаемом формате.',
            'image.max' => 'Изображение больше 5 МБ: уменьшите файл и попробуйте ещё раз.',
        ]);

        $entry = MuseumEntry::findOrFail($validated['museum_entry_id']);
        $this->requireEntry($entry);
        $upload = $request->file('image');
        $raw = file_get_contents($upload->getRealPath());
        if (! is_string($raw)) {
            throw ValidationException::withMessages(['image' => 'Не удалось прочитать файл.']);
        }
        $extension = strtolower($upload->getClientOriginalExtension());
        if ($extension === 'svg') {
            [$raw, $width, $height] = $svgRasterizer->render($raw);
        } else {
            $types = ['png' => IMAGETYPE_PNG, 'jpg' => IMAGETYPE_JPEG,
                'jpeg' => IMAGETYPE_JPEG, 'webp' => IMAGETYPE_WEBP, 'gif' => IMAGETYPE_GIF];
            $details = @getimagesizefromstring($raw);
            if (! isset($types[$extension]) || $details === false || $details[2] !== $types[$extension]) {
                throw ValidationException::withMessages(['image' => 'Недопустимый формат изображения.']);
            }
            [$width, $height] = $details;
        }
        if ($width < 1 || $height < 1 || $width > 4096 || $height > 4096 || $width * $height > 16000000) {
            throw ValidationException::withMessages(['image' => 'Изображение превышает ограничения.']);
        }

        $clean = null;
        if ($extension === 'gif') {
            [$frameCount] = $gifProcessor->inspect($raw, $width, $height);
            if ($frameCount > 1) {
                $clean = $gifProcessor->convertAnimation($raw, $width, $height);
            }
        }
        if ($clean === null) {
            $source = @imagecreatefromstring($raw);
            if ($source === false) {
                throw ValidationException::withMessages(['image' => 'Изображение повреждено.']);
            }
            // Static indexed sources need palette conversion for GD WebP.
            // Animated GIFs use the separately validated libwebp animation path.
            if (imageistruecolor($source) === false && ! imagepalettetotruecolor($source)) {
                imagedestroy($source);
                throw ValidationException::withMessages(['image' => 'Не удалось обработать цветовую палитру.']);
            }
            // Decode and re-encode: discard EXIF, scripts, metadata and original name.
            ob_start();
            $encoded = imagewebp($source, null, 82);
            $clean = ob_get_clean();
            imagedestroy($source);
            if (! $encoded || ! is_string($clean)) {
                throw ValidationException::withMessages(['image' => 'Не удалось безопасно обработать файл.']);
            }
        }

        if (! is_string($clean) || $clean === '' || strlen($clean) > 5242880) {
            throw ValidationException::withMessages(['image' => 'Не удалось безопасно обработать файл.']);
        }
        $path = 'museum/media/'.Str::uuid().'.webp';
        if (! Storage::disk('local')->put($path, $clean)) {
            abort(500, 'Unable to store uploaded image');
        }

        try {
            MuseumMedia::query()->create([
                'museum_entry_id' => $validated['museum_entry_id'],
                'storage_path' => $path,
                'sha256' => hash('sha256', $clean),
                'alt' => $validated['alt'],
                'caption' => $validated['caption'] ?? null,
                'long_description' => $validated['long_description'] ?? null,
                'mime' => 'image/webp',
                'width' => $width,
                'height' => $height,
                'size_bytes' => strlen($clean),
                'uploaded_by' => MoonShineAuth::getGuard()->id(),
            ]);
        } catch (\Throwable $e) {
            Storage::disk('local')->delete($path);
            throw $e;
        }

        return $context->redirect($request, 'museum.media.index', 'Изображение добавлено.');
    }

    public function update(Request $request, MuseumMedia $media, MuseumWorkflowEntry $context): RedirectResponse
    {
        $validated = $request->validate([
            'museum_entry_id' => ['required', 'integer', 'exists:museum_entries,id'],
            'alt' => ['required', 'string', 'min:3', 'max:'.MuseumAltPolicy::MAX_LENGTH,
                static function (string $field, mixed $value, \Closure $fail): void {
                    if ($issue = MuseumAltPolicy::issue(is_string($value) ? $value : null)) $fail($issue);
                }],
            'long_description' => ['nullable', 'string', 'max:3000'],
            'caption' => ['nullable', 'string', 'max:255'],
        ]);

        $this->requireEntry($media->entry);
        $this->requireEntry(MuseumEntry::findOrFail($validated['museum_entry_id']));
        $media->update($validated);

        return $context->redirect($request, 'museum.media.index', 'Подпись и привязка обновлены.');
    }

    public function destroy(Request $request, MuseumMedia $media, MuseumWorkflowEntry $context): RedirectResponse
    {
        $this->requireEntry($media->entry);
        $path = $media->storage_path;
        $media->delete();
        Storage::disk('local')->delete($path);

        return $context->redirect($request, 'museum.media.index', 'Изображение удалено.');
    }

    public function preview(MuseumMedia $media): Response
    {
        $this->requireEntry($media->entry);
        // Media preview must enforce the same content-addressed integrity as
        // private document download and static export. A disk-side mutation
        // must never be served as a previously reviewed museum image.
        $path = Storage::disk('local')->path($media->storage_path);
        if (! is_file($path) || is_link($path)
            || filesize($path) !== (int) $media->size_bytes) abort(404);
        // Read once, validate EXACT bytes being returned. Hashing the path
        // before a second read would leave a file-replacement race window.
        $image = file_get_contents($path);
        if (! is_string($image)
            || strlen($image) !== (int) $media->size_bytes
            || ! hash_equals((string) $media->sha256, hash('sha256', $image))
            || (@getimagesizefromstring($image)[2] ?? null) !== IMAGETYPE_WEBP) {
            abort(404);
        }

        return response($image, 200, [
            'Content-Type' => 'image/webp',
            'X-Content-Type-Options' => 'nosniff',
            'Cache-Control' => 'private, max-age=300',
            'Content-Security-Policy' => "default-src 'none'; sandbox",
        ]);
    }
}
