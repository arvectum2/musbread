<?php

declare(strict_types=1);

namespace App\Support;

use App\Models\MuseumSection;
use Illuminate\Support\Collection;

/** One fail-closed ancestor-publication policy for CMS listing and export.
 *
 * A published child is not public if any parent is draft, missing or cyclic.
 * This does not grant approvals; MuseumExplicitApprovalGate is still required
 * for strict editorial release.
 */
final class MuseumPublishedSections
{
    /** @param Collection<int, MuseumSection> $sections
     *  @return Collection<int, MuseumSection>
     */
    public static function filter(Collection $sections): Collection
    {
        $byId = $sections->keyBy('id');

        return $sections->filter(static function (MuseumSection $section) use ($byId): bool {
            $seen = [];
            $node = $section;
            while ($node !== null) {
                if ($node->status !== 'published' || isset($seen[$node->id])) return false;
                $seen[$node->id] = true;
                if ($node->parent_id !== null && ! $byId->has($node->parent_id)) return false;
                $node = $node->parent_id === null ? null : $byId->get($node->parent_id);
            }
            return true;
        });
    }
}
