<?php

declare(strict_types=1);

namespace App\Support;

use App\Models\MuseumContentApproval;
use App\Models\MuseumEntry;
use App\Models\MuseumEvent;
use App\Models\MuseumFixedPageSeo;
use App\Models\MuseumSection;
use App\Models\MuseumVisitorContacts;
use RuntimeException;

/**
 * Fail-closed pre-award approval mode for PRIVATE exports only.
 * Never silently interpret a 'published' flag as an editorial decision.
 */
final class MuseumExplicitApprovalGate
{
    public function assertApproved(): void
    {
        if (! config('museum.editorial_approval_queue', false)) {
            return;
        }

        // Until the museum authorizes the workflow and durable infrastructure,
        // this opt-in switch must NEVER weaken a legacy export path.
        if (! config('museum.queue_publication', false)
            || ! in_array(config('queue.default'), ['database', 'redis'], true)
            || ! in_array(config('cache.default'), ['database', 'redis'], true)) {
            throw new RuntimeException('Explicit approval requires persistent queue and lock configuration.');
        }

        // The current approval journal covers MuseumEntry ONLY. Fail the whole
        // export rather than let sections, events or fixed site data bypass it.
        // Additional editorial approval workflows must be built before enabling
        // this mode for a populated museum site.
        if (MuseumSection::query()->where('status', 'published')->exists()
            || MuseumEvent::query()->public()->exists()
            || MuseumFixedPageSeo::query()->where('status', 'published')->exists()
            || MuseumVisitorContacts::query()->where('status', 'published')->exists()) {
            throw new RuntimeException('Explicit approval for sections, events and site metadata is not implemented; export denied.');
        }

        foreach (MuseumEntry::query()->public()->get() as $entry) {
            $fingerprint = MuseumApprovalRevision::fingerprint($entry);
            $exists = MuseumContentApproval::query()
                ->where('museum_entry_id', $entry->id)
                ->where('revision_sha256', $fingerprint)
                ->where('dispatch_status', 'queued')
                ->exists();

            if (! $exists) {
                // Never echo unpublished content or editorial fingerprints in logs.
                throw new RuntimeException('Unapproved public entry in strict mode, ID '.$entry->id);
            }
        }
    }
}
