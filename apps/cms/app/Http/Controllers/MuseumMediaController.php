<?php

namespace App\Http\Controllers;

use App\Models\MuseumEntry;
use App\Models\MuseumMedia;
use Illuminate\Http\RedirectResponse;
use Illuminate\Http\Request;
use Illuminate\Http\Response;
use Illuminate\Support\Facades\Storage;
use Illuminate\Support\Str;
use Illuminate\Validation\ValidationException;
use MoonShine\Laravel\MoonShineAuth;

final class MuseumMediaController extends Controller
{
    public function index(): \Illuminate\Contracts\View\View
    {
        return view('media.index', [
            'entries' => MuseumEntry::query()->orderBy('title')->get(['id', 'title', 'slug', 'status']),
            'media' => MuseumMedia::query()->with('entry:id,title,status')->latest()->paginate(30),
        ]);
    }

    public function store(Request $request): RedirectResponse
    {
        $validated = $request->validate([
            'museum_entry_id' => ['required', 'integer', 'exists:museum_entries,id'],
            'alt' => ['required', 'string', 'min:3', 'max:255'],
            'caption' => ['nullable', 'string', 'max:255'],
            'image' => ['required', 'file', 'image', 'mimes:jpeg,jpg,png,webp', 'max:5120',
                'dimensions:max_width=4096,max_height=4096'],
        ]);

        $upload = $request->file('image');
        $raw = file_get_contents($upload->getRealPath());
        $details = @getimagesizefromstring($raw);
        $allowed = [IMAGETYPE_PNG, IMAGETYPE_JPEG, IMAGETYPE_WEBP];
        if ($details === false || ! in_array($details[2], $allowed, true)) {
            throw ValidationException::withMessages(['image' => 'Недопустимый формат изображения.']);
        }
        [$width, $height] = $details;
        if ($width < 1 || $height < 1 || $width * $height > 16000000) {
            throw ValidationException::withMessages(['image' => 'Изображение превышает ограничения.']);
        }

        $source = @imagecreatefromstring($raw);
        if ($source === false) {
            throw ValidationException::withMessages(['image' => 'Изображение повреждено.']);
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

        $media->update($validated);

        return redirect()->route('museum.media.index')->with('status', 'Подпись и привязка обновлены.');
    }

    public function destroy(MuseumMedia $media): RedirectResponse
    {
        $path = $media->storage_path;
        $media->delete();
        Storage::disk('local')->delete($path);

        return redirect()->route('museum.media.index')->with('status', 'Изображение удалено.');
    }

    public function preview(MuseumMedia $media): Response
    {
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
