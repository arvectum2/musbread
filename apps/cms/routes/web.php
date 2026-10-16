<?php

use Illuminate\Support\Facades\Route;

Route::get('/', function () {
    return view('welcome');
});

// The private media library lives alongside the CMS and uses its auth guard.
// The raw files are never served directly by Laravel's public storage route.
Route::middleware(\MoonShine\Laravel\Http\Middleware\Authenticate::class)->group(function () {
    Route::get('/admin/museum-documents', [\App\Http\Controllers\MuseumDocumentController::class, 'index'])->name('museum.documents.index');
    Route::post('/admin/museum-documents', [\App\Http\Controllers\MuseumDocumentController::class, 'store'])->name('museum.documents.store');
    Route::get('/admin/museum-documents/{document}/download', [\App\Http\Controllers\MuseumDocumentController::class, 'download'])->name('museum.documents.download');
    Route::patch('/admin/museum-documents/{document}/accessibility', [\App\Http\Controllers\MuseumDocumentController::class, 'accessibility'])->name('museum.documents.accessibility');
    Route::delete('/admin/museum-documents/{document}', [\App\Http\Controllers\MuseumDocumentController::class, 'destroy'])->name('museum.documents.destroy');
    Route::get('/admin/museum-sections/tree', [\App\Http\Controllers\MuseumSectionTreeController::class, 'index'])->name('museum.sections.tree');
    Route::post('/admin/museum-sections/{section}/reorder', [\App\Http\Controllers\MuseumSectionTreeController::class, 'reorder'])->name('museum.sections.reorder');
    Route::get('/admin/museum-events/{event}/preview', [\App\Http\Controllers\MuseumEventPreviewController::class, 'show'])->name('museum.events.preview');
    Route::get('/admin/museum-content/preflight', [\App\Http\Controllers\MuseumContentPreflightController::class, 'index'])->name('museum.content.preflight');
    Route::get('/admin/museum-entries/{entry}/relations', [\App\Http\Controllers\MuseumContentRelationsController::class, 'edit'])->name('museum.entries.relations.edit');
    Route::put('/admin/museum-entries/{entry}/relations', [\App\Http\Controllers\MuseumContentRelationsController::class, 'update'])->name('museum.entries.relations.update');
    Route::get('/admin/museum-entries/{entry}/preview', [\App\Http\Controllers\MuseumEntryPreviewController::class, 'show'])->name('museum.entries.preview');
    Route::get('/admin/museum-media', [\App\Http\Controllers\MuseumMediaController::class, 'index'])->name('museum.media.index');
    Route::post('/admin/museum-media', [\App\Http\Controllers\MuseumMediaController::class, 'store'])->name('museum.media.store');
    Route::patch('/admin/museum-media/{media}', [\App\Http\Controllers\MuseumMediaController::class, 'update'])->name('museum.media.update');
    Route::delete('/admin/museum-media/{media}', [\App\Http\Controllers\MuseumMediaController::class, 'destroy'])->name('museum.media.destroy');
    Route::get('/admin/museum-media/{media}/preview', [\App\Http\Controllers\MuseumMediaController::class, 'preview'])->name('museum.media.preview');
});
