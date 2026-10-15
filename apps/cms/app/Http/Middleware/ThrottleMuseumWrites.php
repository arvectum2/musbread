<?php

namespace App\Http\Middleware;

use Closure;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\RateLimiter;
use Symfony\Component\HttpFoundation\Response;

final class ThrottleMuseumWrites
{
    /**
     * This is an additional application-level safety net. Museum Nginx
     * will also limit these endpoints after the customer network is known.
     * Key on client IP, not submitted username, to prevent account rotation
     * from bypassing the budget. Do not trust X-Forwarded-For by default.
     */
    public function handle(Request $request, Closure $next): Response
    {
        $budget = match (true) {
            $request->isMethod('POST') && $request->is('admin/authenticate') => ['login', 8],
            $request->isMethod('POST') && $request->is('admin/museum-media') => ['upload', 30],
            default => null,
        };

        if ($budget !== null) {
            [$scope, $limit] = $budget;
            $key = 'musbread:rate:'.$scope.':'.hash('sha256', (string) $request->ip());
            if (RateLimiter::tooManyAttempts($key, $limit)) {
                return response('Too many requests. Try again later.', 429)
                    ->header('Retry-After', (string) max(1, RateLimiter::availableIn($key)));
            }

            RateLimiter::hit($key, 60);
        }

        return $next($request);
    }
}
