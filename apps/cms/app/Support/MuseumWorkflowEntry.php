<?php

declare(strict_types=1);

namespace App\Support;

use App\Models\MuseumEntry;
use Illuminate\Http\RedirectResponse;
use Illuminate\Http\Request;
use MoonShine\Laravel\Models\MoonshineUser;

/** Query string entry is only navigation context, never access authorization. */
final class MuseumWorkflowEntry
{
    public function selected(Request $request, MoonshineUser $actor): ?MuseumEntry
    {
        $id = $request->query('entry');
        if ($id === null) return null;
        if (! is_string($id) || ! ctype_digit($id) || (int) $id < 1) abort(404);

        return MuseumEntry::query()->editableBy($actor)->findOrFail((int) $id);
    }

    public function redirect(Request $request, string $route, string $message): RedirectResponse
    {
        // GET must recheck access even when the query is supplied by a POST.
        $id = $request->query('entry');
        $params = is_string($id) && ctype_digit($id) && (int) $id > 0
            ? ['entry' => (int) $id] : [];

        return redirect()->route($route, $params)->with('status', $message);
    }
}
