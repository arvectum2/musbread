<?php

declare(strict_types=1);

namespace App\Http\Controllers;

use App\Models\MuseumEditorialReviewNote;
use App\Support\MuseumPublicationDiff;
use App\Support\MuseumSectionAccess;
use Illuminate\Http\RedirectResponse;
use Illuminate\Http\Request;
use Illuminate\Http\Response;

/** Private append-only internal notes bound to the exact two content hashes. */
final class MuseumEditorialReviewNotesController extends Controller
{
    private function requireAdmin(): void
    {
        if (! MuseumSectionAccess::user()?->isSuperUser()) abort(403);
    }

    private function comparison(MuseumPublicationDiff $diff): array
    {
        $comparison = $diff->report(MuseumSectionAccess::user());
        if (! $comparison['baseline_available']) abort(409, 'Невозможно обсуждать изменения без проверенной локальной базы.');
        return $comparison;
    }

    private function headers(): array
    {
        return [
            'Cache-Control' => 'private, no-store, max-age=0',
            'Pragma' => 'no-cache',
            'X-Robots-Tag' => 'noindex, nofollow, noarchive',
            'X-Content-Type-Options' => 'nosniff',
            'X-Frame-Options' => 'DENY',
            'Referrer-Policy' => 'no-referrer',
            'Content-Security-Policy' => "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; base-uri 'none'; frame-ancestors 'none'",
        ];
    }

    public function index(MuseumPublicationDiff $diff): Response
    {
        $this->requireAdmin();
        $comparison = $this->comparison($diff);
        $current = MuseumEditorialReviewNote::query()
            ->where('baseline_sha256', $comparison['baseline_sha256'])
            ->where('candidate_sha256', $comparison['candidate_sha256'])
            ->orderBy('id')->get()->groupBy(static fn ($note) => $note->item_group.':'.$note->item_key);
        $priorCount = MuseumEditorialReviewNote::query()
            ->where(static fn ($query) => $query->where('baseline_sha256', '!=', $comparison['baseline_sha256'])
                ->orWhere('candidate_sha256', '!=', $comparison['candidate_sha256']))
            ->count();
        return response()->view('entries.editorial-review', compact('comparison', 'current', 'priorCount'), 200, $this->headers());
    }

    public function store(Request $request, MuseumPublicationDiff $diff): RedirectResponse
    {
        $this->requireAdmin();
        $input = $request->validate([
            'baseline_sha256' => ['required', 'regex:/^[a-f0-9]{64}$/D'],
            'candidate_sha256' => ['required', 'regex:/^[a-f0-9]{64}$/D'],
            'item_group' => ['required', 'in:entries,events,sections'],
            'item_key' => ['required', 'string', 'max:200'],
            'decision' => ['required', 'in:comment,needs_changes,checked'],
            'note' => ['required', 'string', 'min:3', 'max:1200'],
        ]);
        $comparison = $this->comparison($diff);
        if (! hash_equals($comparison['candidate_sha256'], $input['candidate_sha256'])
            || ! hash_equals($comparison['baseline_sha256'], $input['baseline_sha256'])) {
            abort(409, 'Данные изменились. Повторите проверку текущего снимка.');
        }
        $matches = collect($comparison['groups'][$input['item_group']] ?? [])
            ->contains(static fn ($row) => $row['key'] === $input['item_key'] && $row['action'] !== 'unchanged');
        if (! $matches) abort(422, 'Указанный объект не изменялся в текущем снимке.');
        MuseumEditorialReviewNote::query()->create([
            ...$input, 'actor_id' => MuseumSectionAccess::user()->getKey(),
        ]);
        return redirect()->route('museum.content.editorial-review', [], 303);
    }
}
