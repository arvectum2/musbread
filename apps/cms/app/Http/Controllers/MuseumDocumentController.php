<?php

namespace App\Http\Controllers;

use App\Models\MuseumDocument;
use App\Models\MuseumEntry;
use App\Support\MuseumDocumentInspector;
use App\Support\MuseumSectionAccess;
use Illuminate\Auth\Access\AuthorizationException;
use Illuminate\Contracts\View\View;
use Illuminate\Http\RedirectResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Storage;
use Illuminate\Support\Str;
use Symfony\Component\HttpFoundation\BinaryFileResponse;

final class MuseumDocumentController extends Controller
{
    private function requireEntry(MuseumEntry $entry): void
    {
        if (! MuseumSectionAccess::mayEdit(MuseumSectionAccess::user(), $entry->museum_section_id)) {
            throw new AuthorizationException('Нет прав на материалы этого раздела.');
        }
    }

    public function index(): View
    {
        $user = MuseumSectionAccess::user();
        if ($user === null) throw new AuthorizationException();
        $entries = MuseumEntry::query()->editableBy($user)->orderBy('title')->get(['id', 'title', 'slug']);
        $documents = MuseumDocument::query()->with('entry:id,title,museum_section_id')
            ->whereIn('museum_entry_id', $entries->pluck('id'))
            ->latest()->paginate(30);
        return view('documents.index', compact('entries', 'documents'));
    }

    public function store(Request $request, MuseumDocumentInspector $inspector): RedirectResponse
    {
        $validated = $request->validate([
            'museum_entry_id' => ['required', 'integer', 'exists:museum_entries,id'],
            'label' => ['required', 'string', 'min:3', 'max:180'],
            'document' => ['required', 'file', 'max:15360'],
        ]);
        $entry = MuseumEntry::findOrFail($validated['museum_entry_id']);
        $this->requireEntry($entry);

        $upload = $request->file('document');
        $ext = strtolower($upload->getClientOriginalExtension());
        $inspector->verify($upload->getRealPath(), $ext);
        $raw = file_get_contents($upload->getRealPath());
        if (! is_string($raw)) abort(422);

        $sha = hash('sha256', $raw);
        $path = 'museum/documents/'.Str::uuid().'.'.$ext;
        if (! Storage::disk('local')->put($path, $raw)) abort(500);
        try {
            MuseumDocument::create([
                'museum_entry_id' => $entry->id,
                'label' => $validated['label'],
                'file_type' => $ext,
                'storage_path' => $path,
                'sha256' => $sha,
                'size_bytes' => strlen($raw),
                'uploaded_by' => MuseumSectionAccess::user()?->id,
            ]);
        } catch (\Throwable $error) {
            Storage::disk('local')->delete($path);
            throw $error;
        }
        return redirect()->route('museum.documents.index')->with('status', 'Документ загружен.');
    }

    public function destroy(MuseumDocument $document): RedirectResponse
    {
        $this->requireEntry($document->entry);
        $path = $document->storage_path;
        $document->delete();
        Storage::disk('local')->delete($path);
        return redirect()->route('museum.documents.index')->with('status', 'Документ удалён.');
    }

    public function download(MuseumDocument $document, MuseumDocumentInspector $inspector): BinaryFileResponse
    {
        $this->requireEntry($document->entry);
        $path = Storage::disk('local')->path($document->storage_path);
        if (! is_file($path) || hash_file('sha256', $path) !== $document->sha256 ||
            filesize($path) !== $document->size_bytes) abort(404);
        $inspector->verify($path, $document->file_type);
        $download = response()->download($path, 'museum-document-'.$document->id.'.'.$document->file_type, [
            'Content-Type' => 'application/octet-stream',
            'X-Content-Type-Options' => 'nosniff',
            'Content-Security-Policy' => "default-src 'none'; sandbox",
        ]);
        $download->setPrivate();
        $download->headers->set('Cache-Control', 'private, no-store');
        return $download;
    }
}
