<?php

declare(strict_types=1);

namespace Tests\Unit;

use App\Support\MuseumEditorialReviewSummary;
use PHPUnit\Framework\TestCase;

final class MuseumEditorialReviewSummaryTest extends TestCase
{
    public function test_latest_internal_decision_controls_counts_and_attention_priority(): void
    {
        $groups = [
            'entries' => [
                ['key' => 'news:pending', 'title' => 'Не рассмотрено', 'action' => 'changed'],
                ['key' => 'news:fixed', 'title' => 'Проверено', 'action' => 'changed'],
                ['key' => 'news:reopened', 'title' => 'Исправить снова', 'action' => 'added'],
                ['key' => 'news:untouched', 'title' => 'Не менялось', 'action' => 'unchanged'],
            ],
            'events' => [['key' => 'autumn', 'title' => 'Есть комментарий', 'action' => 'removed']],
        ];
        $notes = collect([
            'entries:news:fixed' => collect([
                (object) ['decision' => 'needs_changes'], (object) ['decision' => 'checked'],
            ]),
            'entries:news:reopened' => collect([
                (object) ['decision' => 'checked'], (object) ['decision' => 'needs_changes'],
            ]),
            'events:autumn' => collect([(object) ['decision' => 'comment']]),
            'entries:news:untouched' => collect([(object) ['decision' => 'needs_changes']]),
            'entries:news:secret' => collect([(object) ['decision' => 'needs_changes']]),
        ]);
        $summary = (new MuseumEditorialReviewSummary())->build($groups, $notes);
        $this->assertSame(['unreviewed' => 1, 'comment' => 1, 'needs_changes' => 1, 'checked' => 1], $summary['counts']);
        $this->assertSame(['news:reopened', 'autumn', 'news:pending'], array_column($summary['attention'], 'key'));
        $this->assertSame('checked', $summary['state']['entries:news:fixed']);
        $this->assertSame('needs_changes', $summary['state']['entries:news:reopened']);
        $this->assertArrayNotHasKey('entries:news:secret', $summary['state']);
        $this->assertArrayNotHasKey('entries:news:untouched', $summary['state']);
    }

    public function test_empty_or_already_checked_scope_is_not_automatically_approved(): void
    {
        $service = new MuseumEditorialReviewSummary();
        $this->assertSame(['unreviewed' => 0, 'comment' => 0, 'needs_changes' => 0, 'checked' => 0],
            $service->build(['entries' => []], collect())['counts']);
        $notes = collect(['entries:news:one' => collect([(object) ['decision' => 'checked']])]);
        $checked = $service->build(['entries' => [[
            'key' => 'news:one', 'title' => 'Готово внутренне', 'action' => 'changed',
        ]]], $notes);
        $this->assertSame([], $checked['attention']);
        $this->assertSame(1, $checked['counts']['checked']);
    }
}
