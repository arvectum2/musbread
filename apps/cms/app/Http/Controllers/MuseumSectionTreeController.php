<?php

declare(strict_types=1);

namespace App\Http\Controllers;

use App\Models\MuseumSection;
use App\Support\MuseumSectionAccess;
use Illuminate\Http\RedirectResponse;
use Illuminate\Http\Request;
use Illuminate\Http\Response;
use Illuminate\Support\Facades\DB;
use Illuminate\Validation\ValidationException;

/** Administrator-only overview and safe sibling ordering; existing CRUD owns editing. */
final class MuseumSectionTreeController extends Controller
{
    private function requireAdministrator(): void
    {
        $user = MuseumSectionAccess::user();
        if ($user === null || ! $user->isSuperUser()) abort(403);
    }

    public function index(): Response
    {
        $this->requireAdministrator();
        $sections = MuseumSection::query()->withCount([
            'entries', 'editors',
            'entries as approved_entries_count' => static fn ($query) => $query->public(),
        ])->get();
        $ordered = $sections->sort(static fn ($a, $b) =>
            ($a->sort_order <=> $b->sort_order)
                ?: strcmp($a->slug, $b->slug)
                ?: ($a->id <=> $b->id));
        $children = $ordered->groupBy(static fn ($item) => $item->parent_id ?? 0);
        $rows = [];
        $seen = [];
        $visit = function (MuseumSection $section, int $depth, bool $ancestorsPublished) use (&$visit, &$rows, &$seen, $children): void {
            if (isset($seen[$section->id])) return; // defensive protection against malformed imported trees
            $seen[$section->id] = true;
            $selfPublished = $section->status === 'published';
            $visible = $ancestorsPublished && $selfPublished;
            $status = ! $selfPublished ? 'draft' : ($ancestorsPublished ? 'visible' : 'blocked');
            $siblings = $children->get($section->parent_id ?? 0, collect());
            $rows[] = [
                'section' => $section,
                'depth' => $depth,
                'status' => $status,
                'visible_entries' => $visible ? $section->approved_entries_count : 0,
                'can_move_up' => $siblings->isNotEmpty() && $siblings->first()->id !== $section->id,
                'can_move_down' => $siblings->isNotEmpty() && $siblings->last()->id !== $section->id,
            ];
            foreach ($children->get($section->id, collect()) as $child) {
                $visit($child, $depth + 1, $visible);
            }
        };
        foreach ($children->get(0, collect()) as $root) {
            $visit($root, 0, true);
        }
        // Invalid imported records are never silently presented as public.
        // Their full branches remain visible to the admin for repair.
        foreach ($ordered as $orphan) {
            if (! isset($seen[$orphan->id])) $visit($orphan, 0, false);
        }

        return response()->view('sections.tree', [
            'rows' => $rows,
            'total' => count($rows),
            'visible' => count(array_filter($rows, static fn ($row) => $row['status'] === 'visible')),
            'blocked' => count(array_filter($rows, static fn ($row) => $row['status'] === 'blocked')),
            'draft' => count(array_filter($rows, static fn ($row) => $row['status'] === 'draft')),
            'visibleEntries' => array_sum(array_column($rows, 'visible_entries')),
        ], 200, [
            'Cache-Control' => 'private, no-store, max-age=0',
            'X-Robots-Tag' => 'noindex, nofollow, noarchive',
            'X-Frame-Options' => 'DENY',
            'Referrer-Policy' => 'no-referrer',
            'Content-Security-Policy' => "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; base-uri 'none'; frame-ancestors 'none'",
        ]);
    }

    public function reorder(Request $request, string $section): RedirectResponse
    {
        $this->requireAdministrator();
        if (! ctype_digit($section)) abort(404);
        $data = $request->validate(['direction' => ['required', 'in:up,down']]);
        DB::transaction(static function () use ($section, $data): void {
            $target = MuseumSection::query()->lockForUpdate()->findOrFail($section);
            $siblings = MuseumSection::query()
                ->where('parent_id', $target->parent_id)
                ->orderBy('sort_order')->orderBy('slug')->orderBy('id')
                ->lockForUpdate()->get();
            $index = $siblings->search(static fn ($item) => $item->id === $target->id);
            if ($index === false) abort(404);
            $neighbor = $data['direction'] === 'up' ? $index - 1 : $index + 1;
            if ($neighbor < 0 || $neighbor >= $siblings->count()) {
                throw ValidationException::withMessages([
                    'direction' => 'В выбранном направлении соседнего раздела нет.',
                ]);
            }
            // Re-index each sibling so equal initial sort_order values also move
            // predictably; never touch other parents' sections or statuses.
            $ids = $siblings->pluck('id')->all();
            [$ids[$index], $ids[$neighbor]] = [$ids[$neighbor], $ids[$index]];
            if (count($ids) > 1000001) abort(422);
            $byId = $siblings->keyBy('id');
            foreach ($ids as $position => $id) {
                // Use model events so the existing editorial audit trail records
                // changes and actor ID; raw query updates bypass the observer.
                $model = $byId->get($id);
                if ($model->sort_order !== $position) {
                    $model->update(['sort_order' => $position]);
                }
            }
        });

        return redirect()->route('museum.sections.tree')
            ->with('status', 'Порядок соседних разделов обновлён. Публичное меню изменится после очередной публикации.');
    }
}
