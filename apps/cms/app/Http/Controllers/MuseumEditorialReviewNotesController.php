<?php

declare(strict_types=1);

namespace App\Http\Controllers;

use App\Models\MuseumEditorialReviewNote;
use App\Models\MuseumEditorialTaskUpdate;
use App\Models\MuseumEntry;
use App\Support\MuseumPublicationDiff;
use App\Support\MuseumEditorialReviewSummary;
use App\Support\MuseumSectionAccess;
use Illuminate\Http\RedirectResponse;
use Illuminate\Http\Request;
use Illuminate\Http\Response;
use MoonShine\Laravel\Models\MoonshineUser;

/** Private append-only internal notes bound to the exact two content hashes. */
final class MuseumEditorialReviewNotesController extends Controller
{
    private function user(): MoonshineUser
    {
        $user = MuseumSectionAccess::user();
        if ($user === null) abort(403);
        // A role name alone is never sufficient; editors require explicit grants.
        if (! $user->isSuperUser() && MuseumSectionAccess::allowedIds($user) === []) abort(403);
        return $user;
    }

    private function comparison(MuseumPublicationDiff $diff, MoonshineUser $user): array
    {
        $comparison = $diff->report($user);
        if (! $comparison['baseline_available']) abort(409, 'Невозможно обсуждать изменения без проверенной локальной базы.');
        if (! $user->isSuperUser()) {
            // The diff also includes global events and historical entries which
            // may have MOVED to a forbidden section. Editors may review only
            // entry keys currently owned by one of their granted sections.
            $owned = MuseumEntry::query()->editableBy($user)
                ->get(['type', 'slug'])
                ->mapWithKeys(static fn (MuseumEntry $entry) => [$entry->type.':'.$entry->slug => true])
                ->all();
            $comparison['groups'] = ['entries' => array_values(array_filter(
                $comparison['groups']['entries'] ?? [],
                static fn (array $row) => isset($owned[$row['key']])
            ))];
        }
        return $comparison;
    }

    /** Query only item keys actually visible in the user's current scoped diff. */
    private function accessibleNotes(array $comparison, MoonshineUser $user): \Illuminate\Database\Eloquent\Builder
    {
        $query = MuseumEditorialReviewNote::query();
        if (! $user->isSuperUser()) {
            $keys = array_column($comparison['groups']['entries'] ?? [], 'key');
            $query->where('item_group', 'entries')->whereIn('item_key', $keys);
        }
        return $query;
    }

    private function accessibleTasks(array $comparison, MoonshineUser $user): \Illuminate\Database\Eloquent\Builder
    {
        $query = MuseumEditorialTaskUpdate::query();
        if (! $user->isSuperUser()) {
            $keys = array_column($comparison['groups']['entries'] ?? [], 'key');
            $query->where('item_group', 'entries')->whereIn('item_key', $keys);
        }
        return $query;
    }

    /** Only users with CURRENT access to this entry can be responsible. */
    private function eligibleAssignees(string $group, string $key, MoonshineUser $actor): array
    {
        if (! $actor->isSuperUser()) return [$actor->getKey() => 'Я (#'.$actor->getKey().')'];
        $entry = null;
        if ($group === 'entries') {
            $parts = explode(':', $key, 2);
            if (count($parts) === 2) {
                $entry = MuseumEntry::query()->where('type', $parts[0])->where('slug', $parts[1])->first();
            }
        }
        $options = [];
        foreach (MoonshineUser::query()->get() as $user) {
            if ($user->isSuperUser() || ($entry !== null
                && MuseumSectionAccess::mayEdit($user, $entry->museum_section_id))) {
                $options[$user->getKey()] = (string) $user->name.' (#'.$user->getKey().')';
            }
        }
        return $options;
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
        $user = $this->user();
        $comparison = $this->comparison($diff, $user);
        $current = $this->accessibleNotes($comparison, $user)
            ->where('baseline_sha256', $comparison['baseline_sha256'])
            ->where('candidate_sha256', $comparison['candidate_sha256'])
            ->orderBy('id')->get()->groupBy(static fn ($note) => $note->item_group.':'.$note->item_key);
        $priorCount = $this->accessibleNotes($comparison, $user)
            ->where(static fn ($query) => $query->where('baseline_sha256', '!=', $comparison['baseline_sha256'])
                ->orWhere('candidate_sha256', '!=', $comparison['candidate_sha256']))
            ->count();
        $summary = app(MuseumEditorialReviewSummary::class)->build($comparison['groups'], $current);
        $taskHistory = $this->accessibleTasks($comparison, $user)
            ->where('baseline_sha256', $comparison['baseline_sha256'])
            ->where('candidate_sha256', $comparison['candidate_sha256'])
            ->orderBy('id')->get()->groupBy(static fn ($row) => $row->item_group.':'.$row->item_key);
        $taskStats = ['open' => 0, 'in_progress' => 0, 'done' => 0];
        $taskList = [];
        $taskOwners = [];
        foreach ($comparison['groups'] as $group => $rows) {
            foreach ($rows as $row) {
                if ($row['action'] === 'unchanged') continue;
                $k = $group.':'.$row['key'];
                $taskOwners[$k] = $this->eligibleAssignees($group, $row['key'], $user);
                $latest = $taskHistory->get($k)?->last();
                if (! $latest) continue;
                ++$taskStats[$latest->task_status];
                $taskList[] = ['group' => $group, 'key' => $row['key'],
                    'title' => $row['title'], 'status' => $latest->task_status,
                    'priority' => $latest->priority, 'assignee_id' => $latest->assignee_id];
            }
        }
        $taskPriority = ['high' => 0, 'normal' => 1, 'low' => 2];
        usort($taskList, static fn ($a, $b) =>
            (($a['status'] === 'done') <=> ($b['status'] === 'done'))
            ?: ($taskPriority[$a['priority']] <=> $taskPriority[$b['priority']])
            ?: strcmp($a['group'].':'.$a['key'], $b['group'].':'.$b['key']));
        return response()->view('entries.editorial-review',
            compact('comparison', 'current', 'priorCount', 'summary', 'taskHistory', 'taskStats', 'taskList', 'taskOwners', 'user'),
            200, $this->headers());
    }

    public function storeTask(Request $request, MuseumPublicationDiff $diff): RedirectResponse
    {
        $user = $this->user();
        $input = $request->validate([
            'baseline_sha256' => ['required', 'regex:/^[a-f0-9]{64}$/D'],
            'candidate_sha256' => ['required', 'regex:/^[a-f0-9]{64}$/D'],
            'item_group' => ['required', 'in:entries,events,sections'],
            'item_key' => ['required', 'string', 'max:200'],
            'task_status' => ['required', 'in:open,in_progress,done'],
            'priority' => ['required', 'in:low,normal,high'],
            'assignee_id' => ['required', 'integer', 'min:1'],
            'note' => ['required', 'string', 'min:3', 'max:1200'],
        ]);
        $comparison = $this->comparison($diff, $user);
        if (! hash_equals($comparison['baseline_sha256'], $input['baseline_sha256'])
            || ! hash_equals($comparison['candidate_sha256'], $input['candidate_sha256'])) {
            abort(409, 'Версия изменилась: обновите страницу задач.');
        }
        $rowExists = collect($comparison['groups'][$input['item_group']] ?? [])
            ->contains(static fn ($row) => $row['key'] === $input['item_key'] && $row['action'] !== 'unchanged');
        if (! $rowExists) abort(422, 'Нет полномочий для задачи по этому материалу.');
        $eligible = $this->eligibleAssignees($input['item_group'], $input['item_key'], $user);
        if (! isset($eligible[(int) $input['assignee_id']])) abort(422, 'Ответственный не назначен на этот материал.');
        $latest = $this->accessibleTasks($comparison, $user)
            ->where('baseline_sha256', $comparison['baseline_sha256'])
            ->where('candidate_sha256', $comparison['candidate_sha256'])
            ->where('item_group', $input['item_group'])
            ->where('item_key', $input['item_key'])
            ->orderByDesc('id')->first();
        // Editors can update their own task, not take another employee's task.
        if (! $user->isSuperUser() && $latest !== null && (int) $latest->assignee_id !== (int) $user->getKey()) {
            abort(403);
        }
        MuseumEditorialTaskUpdate::query()->create([...$input, 'actor_id' => $user->getKey()]);
        return redirect()->route('museum.content.editorial-review', [], 303);
    }

    public function store(Request $request, MuseumPublicationDiff $diff): RedirectResponse
    {
        $user = $this->user();
        $input = $request->validate([
            'baseline_sha256' => ['required', 'regex:/^[a-f0-9]{64}$/D'],
            'candidate_sha256' => ['required', 'regex:/^[a-f0-9]{64}$/D'],
            'item_group' => ['required', 'in:entries,events,sections'],
            'item_key' => ['required', 'string', 'max:200'],
            'decision' => ['required', 'in:comment,needs_changes,checked'],
            'note' => ['required', 'string', 'min:3', 'max:1200'],
        ]);
        $comparison = $this->comparison($diff, $user);
        if (! hash_equals($comparison['candidate_sha256'], $input['candidate_sha256'])
            || ! hash_equals($comparison['baseline_sha256'], $input['baseline_sha256'])) {
            abort(409, 'Данные изменились. Повторите проверку текущего снимка.');
        }
        $matches = collect($comparison['groups'][$input['item_group']] ?? [])
            ->contains(static fn ($row) => $row['key'] === $input['item_key'] && $row['action'] !== 'unchanged');
        if (! $matches) abort(422, 'Указанный объект не изменялся в текущем снимке.');
        MuseumEditorialReviewNote::query()->create([
            ...$input, 'actor_id' => $user->getKey(),
        ]);
        return redirect()->route('museum.content.editorial-review', [], 303);
    }
}
