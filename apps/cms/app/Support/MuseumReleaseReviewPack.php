<?php

declare(strict_types=1);

namespace App\Support;

use MoonShine\Laravel\Models\MoonshineUser;

/** Ephemeral editorial handoff; neither approval nor a deployment artifact. */
final class MuseumReleaseReviewPack
{
    public const JSON_FLAGS = JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES | JSON_THROW_ON_ERROR;

    /** @return array{document:array<string,mixed>,sha256:string}|null */
    public function prepare(MoonshineUser $user): ?array
    {
        $diff = app(MuseumPublicationDiff::class)->report($user);
        if (! $diff['baseline_available']) return null;

        $changes = [];
        foreach ($diff['groups'] as $group => $rows) {
            $changes[$group] = [];
            foreach ($rows as $row) {
                if ($row['action'] === 'unchanged') continue;
                $changes[$group][] = [
                    'key' => $row['key'], 'title' => $row['title'],
                    'action' => $row['action'], 'changed_fields' => $row['changed_fields'],
                ];
            }
        }
        $preflight = $diff['preflight'];
        $document = [
            'schema_version' => 1,
            'kind' => 'musbread_editorial_review_only',
            'source' => 'verified_local_release_and_ephemeral_cms_export',
            'scope' => $diff['scope'],
            'baseline' => [
                'local_release_id' => $diff['baseline_release'],
                'snapshot_sha256' => $diff['baseline_sha256'],
            ],
            'candidate' => ['snapshot_sha256' => $diff['candidate_sha256']],
            'preflight' => [
                'critical_errors' => $preflight['errors'],
                'warnings' => $preflight['warnings'],
                'automated_strict_check_passes' => $preflight['errors'] === 0,
                'materials_in_scope' => $preflight['total'],
                'events_in_scope' => $preflight['events_total'],
                'materials_ready' => $preflight['ready'],
                'events_ready' => $preflight['events_ready'],
            ],
            'summary' => $diff['summary'],
            'changes' => $changes,
            'removed_urls' => array_map(static fn (array $item) => [
                'path' => $item['path'], 'locale' => $item['locale'],
                'kind' => $item['kind'], 'title' => $item['title'],
                'suggested_redirect' => null,
            ], $diff['removed_urls']),
            'limits' => [
                'not_a_museum_approval', 'not_a_production_deployment',
                'no_redirects_applied', 'external_links_not_verified',
                'file_checksum_is_not_a_digital_signature',
            ],
        ];
        $bytes = json_encode($document, self::JSON_FLAGS);
        return ['document' => $document, 'sha256' => hash('sha256', $bytes)];
    }
}
