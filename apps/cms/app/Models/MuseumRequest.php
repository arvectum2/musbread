<?php

namespace App\Models;

use App\Support\MuseumSectionAccess;
use Illuminate\Auth\Access\AuthorizationException;
use Illuminate\Database\Eloquent\Builder;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use Illuminate\Database\Eloquent\Relations\HasMany;
use Illuminate\Support\Str;
use Illuminate\Validation\ValidationException;
use MoonShine\Laravel\Models\MoonshineUser;

/**
 * Closed-network, synthetic-only request workflow.
 * Deliberately contains NO PII or free-text customer data, and does not have
 * public intake routes. Production ingestion needs a separate legal/security gate.
 */
final class MuseumRequest extends Model
{
    public const TYPES = [
        'feedback' => 'Обратная связь',
        'excursion' => 'Заявка на экскурсию',
    ];
    public const TOPICS = [
        'general' => 'Общий вопрос',
        'visit' => 'Посещение музея',
        'accessibility' => 'Доступная среда',
        'excursion_group' => 'Групповая экскурсия',
        'event' => 'Мероприятие',
    ];
    public const STATUSES = [
        'new' => 'Новое',
        'triaged' => 'Принято в работу',
        'in_progress' => 'В обработке',
        'resolved' => 'Выполнено',
        'rejected' => 'Отклонено',
    ];
    private const TRANSITIONS = [
        'new' => ['triaged', 'rejected'],
        'triaged' => ['in_progress', 'rejected'],
        'in_progress' => ['resolved', 'rejected'],
        'resolved' => ['triaged'],
        'rejected' => ['triaged'],
    ];

    protected $fillable = [
        'type', 'topic', 'status', 'museum_section_id', 'assigned_to_id',
        'preferred_date', 'group_size',
    ];

    protected function casts(): array
    {
        return [
            'museum_section_id' => 'integer',
            'assigned_to_id' => 'integer',
            'group_size' => 'integer',
            'preferred_date' => 'date',
            'resolved_at' => 'datetime',
        ];
    }

    public function section(): BelongsTo
    {
        return $this->belongsTo(MuseumSection::class, 'museum_section_id');
    }

    public function assignedTo(): BelongsTo
    {
        return $this->belongsTo(MoonshineUser::class, 'assigned_to_id');
    }

    public function transitions(): HasMany
    {
        return $this->hasMany(MuseumRequestTransition::class, 'museum_request_id');
    }

    public function scopeVisibleTo(Builder $query, MoonshineUser $user): Builder
    {
        if ($user->isSuperUser()) return $query;
        return $query->where('assigned_to_id', $user->id)
            ->whereIn('museum_section_id', MuseumSectionAccess::allowedIds($user));
    }

    protected static function booted(): void
    {
        static::creating(static function (self $case): void {
            if (app()->environment('production')) {
                throw new AuthorizationException('Демо-заявки не создаются в промышленной среде.');
            }
            $case->reference = 'DEMO-'.strtoupper((string) Str::ulid());
            $case->origin = 'internal_demo';
            $case->status = 'new'; // Never accept a pre-completed fabricated case.
        });

        static::saving(static function (self $case): void {
            $actor = MuseumSectionAccess::user();
            if ($actor !== null && ! $actor->isSuperUser()) {
                if (! $case->exists || (int) $case->getRawOriginal('assigned_to_id') !== $actor->id
                    || ! MuseumSectionAccess::mayEdit($actor, $case->getRawOriginal('museum_section_id'))) {
                    throw new AuthorizationException('Обращение не назначено текущему редактору.');
                }
                foreach (array_keys($case->getDirty()) as $field) {
                    if ($field !== 'status') {
                        throw new AuthorizationException('Редактор может изменять только статус своего обращения.');
                    }
                }
            }

            if (! isset(self::TYPES[$case->type]) || ! isset(self::TOPICS[$case->topic])
                || ! isset(self::STATUSES[$case->status])) {
                throw ValidationException::withMessages(['type' => 'Некорректные атрибуты обращения.']);
            }

            if ($case->exists) {
                if ($case->isDirty('reference') || $case->isDirty('origin') || $case->isDirty('type')) {
                    throw ValidationException::withMessages(['reference' => 'Тип и идентификатор обращения неизменяемы.']);
                }
                if ($case->isDirty('status')) {
                    $previous = $case->getRawOriginal('status');
                    if (! in_array($case->status, self::TRANSITIONS[$previous] ?? [], true)) {
                        throw ValidationException::withMessages(['status' => 'Недопустимый переход статуса.']);
                    }
                }
            }

            if ($case->museum_section_id !== null &&
                ! MuseumSection::query()->whereKey($case->museum_section_id)->exists()) {
                throw ValidationException::withMessages(['museum_section_id' => 'Такого раздела нет.']);
            }
            if ($case->assigned_to_id !== null) {
                $assignee = MoonshineUser::find($case->assigned_to_id);
                if ($assignee === null || $case->museum_section_id === null ||
                    ! MuseumSectionAccess::mayEdit($assignee, $case->museum_section_id)) {
                    throw ValidationException::withMessages([
                        'assigned_to_id' => 'Ответственный должен иметь права на этот раздел.',
                    ]);
                }
            }
            if ($case->type === 'excursion') {
                if ($case->preferred_date === null || ! is_int($case->group_size) ||
                    $case->group_size < 1 || $case->group_size > 100) {
                    throw ValidationException::withMessages([
                        'preferred_date' => 'Для экскурсии обязательны дата и размер группы 1–100.',
                    ]);
                }
            } elseif ($case->preferred_date !== null || $case->group_size !== null) {
                throw ValidationException::withMessages([
                    'preferred_date' => 'Даты и размер группы предназначены только для экскурсий.',
                ]);
            }

            if ($case->isDirty('status') || ! $case->exists) {
                $case->resolved_at = in_array($case->status, ['resolved', 'rejected'], true)
                    ? now() : null;
            }
        });

        static::created(static function (self $case): void {
            $case->appendTransition(null, $case->status);
        });

        static::updated(static function (self $case): void {
            if ($case->wasChanged('status')) {
                $case->appendTransition($case->getPrevious()['status'] ?? null, $case->status);
            }
        });

        static::deleting(static function (): void {
            throw new AuthorizationException('Удаление журнала обращений отключено.');
        });
    }

    private function appendTransition(?string $old, string $new): void
    {
        $record = new MuseumRequestTransition();
        $record->museum_request_id = $this->id;
        $record->from_status = $old;
        $record->to_status = $new;
        $record->actor_id = MuseumSectionAccess::user()?->id;
        $record->save();
    }
}
