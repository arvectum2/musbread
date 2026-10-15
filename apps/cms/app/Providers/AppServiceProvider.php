<?php

namespace App\Providers;

use Illuminate\Support\ServiceProvider;
use App\Models\MuseumEntry;
use App\Models\MuseumEvent;
use App\Models\MuseumMedia;
use App\Models\MuseumSection;
use App\Models\MuseumRequest;
use App\Observers\MuseumContentAuditObserver;

class AppServiceProvider extends ServiceProvider
{
    /**
     * Register any application services.
     */
    public function register(): void
    {
        //
    }

    /**
     * Bootstrap any application services.
     */
    public function boot(): void
    {
        MuseumEntry::observe(MuseumContentAuditObserver::class);
        MuseumEvent::observe(MuseumContentAuditObserver::class);
        MuseumMedia::observe(MuseumContentAuditObserver::class);
        MuseumSection::observe(MuseumContentAuditObserver::class);
        MuseumRequest::observe(MuseumContentAuditObserver::class);
        //
    }
}
