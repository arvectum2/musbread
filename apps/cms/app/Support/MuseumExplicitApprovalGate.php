<?php

declare(strict_types=1);

namespace App\Support;

use App\Models\MuseumContentApproval;
use App\Models\MuseumEntry;
use App\Models\MuseumEvent;
use App\Models\MuseumFixedPageSeo;
use App\Models\MuseumSection;
use App\Models\MuseumVisitorContacts;
use Illuminate\Database\Eloquent\Model;
use RuntimeException;

/** Private-only, explicitly-enabled gate. Not a deployment/acceptance signal. */
final class MuseumExplicitApprovalGate
{
    /**
     * An exact fingerprint of the APPROVED set at the beginning of export.
     * Matching the value just before writing JSON prevents a silent switch
     * between two separately approved versions while preparing a package.
     */
    public function capture(): string
    {
        if (! config('museum.editorial_approval_queue', false)) return '';

        if (! config('museum.queue_publication', false)
            || ! in_array(config('queue.default'), ['database', 'redis'], true)
            || ! in_array(config('cache.default'), ['database', 'redis'], true)) {
            throw new RuntimeException('Explicit approval requires persistent queue and lock configuration.');
        }

        // Site-wide fixed metadata has no approved editorial UI yet; refuse it.
        if (MuseumFixedPageSeo::query()->where('status', 'published')->exists()
            || MuseumVisitorContacts::query()->where('status', 'published')->exists()) {
            throw new RuntimeException('Site-wide metadata approval is not implemented; export denied.');
        }

        $set = [];
        foreach ([
            ['entry', 'museum_entry_id', MuseumEntry::query()->public()->orderBy('id')->get()],
            ['event', 'museum_event_id', MuseumEvent::query()->public()->orderBy('id')->get()],
            ['section', 'museum_section_id', MuseumSection::query()->public()->orderBy('id')->get()],
        ] as [$kind, $key, $subjects]) {
            foreach ($subjects as $subject) {
                $hash = MuseumApprovalRevision::forSubject($subject);
                if (! MuseumContentApproval::query()
                    ->where($key, $subject->getKey())
                    ->where('revision_sha256', $hash)
                    ->where('dispatch_status', 'queued')->exists()) {
                    throw new RuntimeException('Unapproved public '.$kind.' in strict mode, ID '.$subject->getKey());
                }
                $set[] = [$kind, $subject->getKey(), $hash];
            }
        }
        return hash('sha256', json_encode($set, JSON_THROW_ON_ERROR));
    }

    public function assertApproved(): void
    {
        $this->capture();
    }

    public function assertUnchanged(string $initial): void
    {
        if ($initial !== $this->capture()) {
            throw new RuntimeException('Approved publication set changed while preparing export.');
        }
    }
}
