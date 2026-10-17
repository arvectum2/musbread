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
    Route::get('/admin/museum-activity', [\App\Http\Controllers\MuseumUserActivityController::class, 'index'])->name('museum.activity.stats');
    Route::get('/admin/museum-sections/tree', [\App\Http\Controllers\MuseumSectionTreeController::class, 'index'])->name('museum.sections.tree');
    Route::post('/admin/museum-sections/{section}/reorder', [\App\Http\Controllers\MuseumSectionTreeController::class, 'reorder'])->name('museum.sections.reorder');
    Route::get('/admin/museum-events/{event}/preview', [\App\Http\Controllers\MuseumEventPreviewController::class, 'show'])->name('museum.events.preview');
    Route::get('/admin/museum-content/removed-urls.csv', [\App\Http\Controllers\MuseumRemovedUrlsController::class, 'download'])->name('museum.content.removed-urls');
    Route::get('/admin/museum-content/release-review.json', [\App\Http\Controllers\MuseumReleaseReviewPackController::class, 'download'])->name('museum.content.release-review');
    Route::get('/admin/museum-content/review-notes', [\App\Http\Controllers\MuseumEditorialReviewNotesController::class, 'index'])->name('museum.content.editorial-review');
    Route::post('/admin/museum-content/review-tasks', [\App\Http\Controllers\MuseumEditorialReviewNotesController::class, 'storeTask'])->name('museum.content.editorial-task.store');
    Route::post('/admin/museum-content/review-notes', [\App\Http\Controllers\MuseumEditorialReviewNotesController::class, 'store'])->name('museum.content.editorial-review.store');
    Route::get('/admin/museum-content/compare', [\App\Http\Controllers\MuseumPublicationDiffController::class, 'index'])->name('museum.content.compare');
    Route::get('/admin/museum-content/preflight', [\App\Http\Controllers\MuseumContentPreflightController::class, 'index'])->name('museum.content.preflight');
    Route::post('/admin/museum-content/queue-publication', [\App\Http\Controllers\MuseumPublishRequestController::class, 'store'])->name('museum.content.queue-publication');
    Route::post('/admin/museum-entries/{entry}/approve-and-queue', [\App\Http\Controllers\MuseumEditorialApprovalController::class, 'store'])->name('museum.entries.approve-and-queue');
    Route::post('/admin/museum-events/{event}/approve-and-queue', [\App\Http\Controllers\MuseumEditorialApprovalController::class, 'storeEvent'])->name('museum.events.approve-and-queue');
    Route::post('/admin/museum-sections/{section}/approve-and-queue', [\App\Http\Controllers\MuseumEditorialApprovalController::class, 'storeSection'])->name('museum.sections.approve-and-queue');
    Route::get('/admin/museum-content/approval-journal', [\App\Http\Controllers\MuseumEditorialApprovalJournalController::class, 'index'])->name('museum.content.approval-journal');
    Route::get('/admin/museum-content/links', [\App\Http\Controllers\MuseumContextLinksController::class, 'index'])->name('museum.content.links');
    Route::get('/admin/museum-entries/{entry}/relations', [\App\Http\Controllers\MuseumContentRelationsController::class, 'edit'])->name('museum.entries.relations.edit');
    Route::put('/admin/museum-entries/{entry}/relations', [\App\Http\Controllers\MuseumContentRelationsController::class, 'update'])->name('museum.entries.relations.update');
    Route::get('/admin/museum-entries/{entry}/preview', [\App\Http\Controllers\MuseumEntryPreviewController::class, 'show'])->name('museum.entries.preview');
    Route::get('/admin/museum-media', [\App\Http\Controllers\MuseumMediaController::class, 'index'])->name('museum.media.index');
    Route::post('/admin/museum-media', [\App\Http\Controllers\MuseumMediaController::class, 'store'])->name('museum.media.store');
    Route::post('/admin/museum-media/suggest-alt', [\App\Http\Controllers\MuseumMediaController::class, 'suggestAlt'])->name('museum.media.alt-suggest');
    Route::patch('/admin/museum-media/{media}', [\App\Http\Controllers\MuseumMediaController::class, 'update'])->name('museum.media.update');
    Route::delete('/admin/museum-media/{media}', [\App\Http\Controllers\MuseumMediaController::class, 'destroy'])->name('museum.media.destroy');
    Route::get('/admin/museum-media/{media}/preview', [\App\Http\Controllers\MuseumMediaController::class, 'preview'])->name('museum.media.preview');
});
