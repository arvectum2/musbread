<?php

declare(strict_types=1);

namespace App\Http\Controllers;

use App\Models\MuseumContentApproval;
use App\Models\MuseumPublicationRun;
use App\Support\MuseumPublicationJourneyStatus;
use App\Support\MuseumSectionAccess;
use Illuminate\Http\Response;

/** Private admin audit journal. Never a claim of public visibility. */
final class MuseumEditorialApprovalJournalController extends Controller
{
    public function index(MuseumPublicationJourneyStatus $journey): Response
    {
        $actor = MuseumSectionAccess::user();
        if ($actor === null || ! $actor->isSuperUser()) abort(403);

        $approvals = MuseumContentApproval::query()->orderByDesc('id')->limit(100)->get();
        return response()->view('entries.approvals', [
            'journey' => $journey->describe($approvals),
            'runs' => MuseumPublicationRun::query()->orderByDesc('id')->limit(25)->get(),
            'runLabels' => MuseumPublicationJourneyStatus::RUN_LABELS,
        ], 200, [
            'Cache-Control' => 'private, no-store, max-age=0',
            'Pragma' => 'no-cache',
            'X-Robots-Tag' => 'noindex, nofollow, noarchive',
            'X-Content-Type-Options' => 'nosniff',
            'X-Frame-Options' => 'DENY',
            'Referrer-Policy' => 'no-referrer',
            'Content-Security-Policy' => "default-src 'none'; style-src 'unsafe-inline'; "
                ."base-uri 'none'; form-action 'none'; frame-ancestors 'none'",
        ]);
    }
}
