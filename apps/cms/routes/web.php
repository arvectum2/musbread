<?php

use Illuminate\Support\Facades\Route;

Route::get('/', function () {
    return view('welcome');
});

// The private media library lives alongside the CMS and uses its auth guard.
// The raw files are never served directly by Laravel's public storage route.
Route::middleware(\MoonShine\Laravel\Http\Middleware\Authenticate::class)->group(function () {
    Route::get('/admin/museum-media', [\App\Http\Controllers\MuseumMediaController::class, 'index'])->name('museum.media.index');
    Route::post('/admin/museum-media', [\App\Http\Controllers\MuseumMediaController::class, 'store'])->name('museum.media.store');
    Route::patch('/admin/museum-media/{media}', [\App\Http\Controllers\MuseumMediaController::class, 'update'])->name('museum.media.update');
    Route::delete('/admin/museum-media/{media}', [\App\Http\Controllers\MuseumMediaController::class, 'destroy'])->name('museum.media.destroy');
    Route::get('/admin/museum-media/{media}/preview', [\App\Http\Controllers\MuseumMediaController::class, 'preview'])->name('museum.media.preview');
});
