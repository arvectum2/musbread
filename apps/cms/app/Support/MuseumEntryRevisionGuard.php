<?php

declare(strict_types=1);

namespace App\Support;

use App\Models\MuseumEntry;
use Illuminate\Support\Facades\DB;

/**
 * Must run inside the caller's write transaction before applying form fields.
 * The SQL compare-and-swap edit_version claim makes saving safe even if a
 * database lacks row-level SELECT FOR UPDATE support (for example SQLite).
 * SQLite may still fail closed with SQLITE_BUSY on a contested transaction.
 */
final class MuseumEntryRevisionGuard
{
    public function assertCurrent(int $entryId, mixed $submitted): MuseumEntry
    {
        if (! is_string($submitted) || ! preg_match('/^[a-f0-9]{64}$/D', $submitted)) {
            abort(409, 'Редакция материала не подтверждена. Откройте форму повторно.');
        }
        $fresh = MuseumEntry::query()->lockForUpdate()->findOrFail($entryId);
        if (! hash_equals(MuseumApprovalRevision::fingerprint($fresh), $submitted)) {
            abort(409, 'Материал изменён другим редактором. Откройте последнюю версию перед сохранением.');
        }
        // The old read-and-compare guard was not enough: two concurrent
        // transactions could both pass it before either saved. Claim the
        // current version with ONE conditional database UPDATE, inside the
        // same transaction as the subsequent MoonShine field writes.
        $claimed = MuseumEntry::query()
            ->whereKey($entryId)
            ->where('edit_version', (int) $fresh->edit_version)
            ->update(['edit_version' => DB::raw('edit_version + 1')]);
        if ($claimed !== 1) {
            abort(409, 'Другая правка уже сохраняется. Загрузите актуальную редакцию.');
        }
        return $fresh;
    }
}
