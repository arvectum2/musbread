<?php

namespace App\Observers;

use App\Models\MuseumAuditRecord;
use Illuminate\Database\Eloquent\Model;
use MoonShine\Laravel\MoonShineAuth;

/**
 * Database-local append-only operational evidence.
 * Never persist article bodies, passwords, filenames, secrets or request payloads
 * in the audit trail. Only field NAMES are recorded.
 */
final class MuseumContentAuditObserver
{
    public function created(Model $model): void
    {
        $this->record($model, 'created', array_keys($model->getAttributes()));
    }

    public function updated(Model $model): void
    {
        $fields = array_keys($model->getChanges());
        $this->record($model, 'updated', $fields);
    }

    public function deleted(Model $model): void
    {
        $this->record($model, 'deleted', []);
    }

    private function record(Model $model, string $action, array $fields): void
    {
        $fields = array_values(array_diff($fields, ['created_at', 'updated_at']));
        MuseumAuditRecord::query()->create([
            'subject_type' => class_basename($model),
            'subject_id' => $model->getKey(),
            'action' => $action,
            'actor_id' => MoonShineAuth::getGuard()->id(),
            'changed_fields' => $fields,
        ]);
    }
}
