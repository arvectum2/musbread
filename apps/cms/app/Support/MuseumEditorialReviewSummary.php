<?php

declare(strict_types=1);

namespace App\Support;

use Illuminate\Support\Collection;

/** Summary derived ONLY from an already ACL-filtered report and its notes. */
final class MuseumEditorialReviewSummary
{
    public const STATUSES = ['unreviewed', 'comment', 'needs_changes', 'checked'];

    /**
     * @param array<string,list<array<string,mixed>>> $groups
     * @param Collection $notes
     * @return array<string,mixed>
     */
    public function build(array $groups, Collection $notes): array
    {
        $counts = array_fill_keys(self::STATUSES, 0);
        $attention = [];
        $state = [];
        foreach ($groups as $group => $items) {
            foreach ($items as $item) {
                if ($item['action'] === 'unchanged') continue;
                $key = $group.':'.$item['key'];
                // The last appended note is the CURRENT internal state.
                $latest = $notes->get($key)?->last();
                $status = $latest?->decision ?? 'unreviewed';
                if (! in_array($status, self::STATUSES, true)) $status = 'unreviewed';
                ++$counts[$status];
                $state[$key] = $status;
                if ($status !== 'checked') {
                    $attention[] = [
                        'group' => $group, 'key' => $item['key'],
                        'title' => (string) $item['title'], 'status' => $status,
                    ];
                }
            }
        }
        $priority = ['needs_changes' => 0, 'comment' => 1, 'unreviewed' => 2];
        usort($attention, static fn (array $a, array $b) =>
            ($priority[$a['status']] <=> $priority[$b['status']])
            ?: strcmp($a['group'].':'.$a['key'], $b['group'].':'.$b['key']));
        return ['counts' => $counts, 'attention' => $attention, 'state' => $state];
    }
}
