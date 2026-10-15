<?php

namespace App\Http\Controllers;

use App\Models\MuseumEntry;
use App\Models\MuseumMedia;
use App\Support\MuseumSectionAccess;
use App\Support\MuseumSvgRasterizer;
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

    public function index(): \Illuminate\Contracts\View\View
    {
        $user = MuseumSectionAccess::user();
        if ($user === null) throw new AuthorizationException();
        $entries = MuseumEntry::query()->editableBy($user)
            ->orderBy('title')->get(['id', 'title', 'slug', 'status']);
        return view('media.index', [
            'entries' => $entries,
            'media' => MuseumMedia::query()->with('entry:id,title,status')
                ->whereIn('museum_entry_id', $entries->pluck('id'))->latest()->paginate(30),
        ]);
    }

    public function store(Request $request, MuseumSvgRasterizer $svgRasterizer): RedirectResponse
    {
        $validated = $request->validate([
            'museum_entry_id' => ['required', 'integer', 'exists:museum_entries,id'],
            'alt' => ['required', 'string', 'min:3', 'max:255'],
            'caption' => ['nullable', 'string', 'max:255'],
            'image' => ['required', 'file', 'max:5120'],
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

        $source = @imagecreatefromstring($raw);
        if ($source === false) {
            throw ValidationException::withMessages(['image' => 'Изображение повреждено.']);
        }
        // GIFs are palette-based; flatten to a true-color first frame
        // because GD WebP refuses indexed images. Animation is NOT preserved.
        if (imageistruecolor($source) === false && ! imagepalettetotruecolor($source)) {
            imagedestroy($source);
            throw ValidationException::withMessages(['image' => 'Не удалось обработать цветовую палитру.']);
        }
        // Decode and re-encode: discard EXIF, scripts, metadata and original name.
        ob_start();
        $encoded = imagewebp($source, null, 82);
        $clean = ob_get_clean();
        imagedestroy($source);

        if (! $encoded || ! is_string($clean) || $clean === '' || strlen($clean) > 5242880) {
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

        return redirect()->route('museum.media.index')->with('status', 'Изображение добавлено.');
    }

    public function update(Request $request, MuseumMedia $media): RedirectResponse
    {
        $validated = $request->validate([
            'museum_entry_id' => ['required', 'integer', 'exists:museum_entries,id'],
            'alt' => ['required', 'string', 'min:3', 'max:255'],
            'caption' => ['nullable', 'string', 'max:255'],
        ]);

        $this->requireEntry($media->entry);
        $this->requireEntry(MuseumEntry::findOrFail($validated['museum_entry_id']));
        $media->update($validated);

        return redirect()->route('museum.media.index')->with('status', 'Подпись и привязка обновлены.');
    }

    public function destroy(MuseumMedia $media): RedirectResponse
    {
        $this->requireEntry($media->entry);
        $path = $media->storage_path;
        $media->delete();
        Storage::disk('local')->delete($path);

        return redirect()->route('museum.media.index')->with('status', 'Изображение удалено.');
    }

    public function preview(MuseumMedia $media): Response
    {
        $this->requireEntry($media->entry);
        if (! Storage::disk('local')->exists($media->storage_path)) {
            abort(404);
        }

        return response(Storage::disk('local')->get($media->storage_path), 200, [
            'Content-Type' => 'image/webp',
            'X-Content-Type-Options' => 'nosniff',
            'Cache-Control' => 'private, max-age=300',
            'Content-Security-Policy' => "default-src 'none'; sandbox",
        ]);
    }
}
