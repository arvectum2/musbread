<?php

namespace App\Providers;

use Illuminate\Support\ServiceProvider;
use App\Models\MuseumEntry;
use App\Models\MuseumEvent;
use App\Models\MuseumMedia;
use App\Models\MuseumSection;
use App\Models\MuseumFixedPageSeo;
use App\Models\MuseumRequest;
use App\Models\MuseumDocument;
use App\Observers\MuseumContentAuditObserver;
use App\Models\MuseumAuditRecord;
use Illuminate\Auth\Events\Login;
use Illuminate\Auth\Events\Logout;
use Illuminate\Support\Facades\Event;

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
        MuseumFixedPageSeo::observe(MuseumContentAuditObserver::class);
        MuseumRequest::observe(MuseumContentAuditObserver::class);
        MuseumDocument::observe(MuseumContentAuditObserver::class);
        // No credentials or IP addresses are retained. Events from any other
        // application guard MUST NOT be mixed into museum staff statistics.
        Event::listen(Login::class, static function (Login $event): void {
            if ($event->guard !== 'moonshine') return;
            MuseumAuditRecord::query()->create([
                'subject_type' => 'MoonshineUser', 'subject_id' => (int)$event->user->getAuthIdentifier(),
                'action' => 'login', 'actor_id' => (int)$event->user->getAuthIdentifier(), 'changed_fields' => [],
            ]);
        });
        Event::listen(Logout::class, static function (Logout $event): void {
            if ($event->guard !== 'moonshine' || $event->user === null) return;
            MuseumAuditRecord::query()->create([
                'subject_type' => 'MoonshineUser', 'subject_id' => (int)$event->user->getAuthIdentifier(),
                'action' => 'logout', 'actor_id' => (int)$event->user->getAuthIdentifier(), 'changed_fields' => [],
            ]);
        });
        //
    }
}
