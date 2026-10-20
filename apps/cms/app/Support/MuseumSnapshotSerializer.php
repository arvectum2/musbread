<?php

declare(strict_types=1);

namespace App\Support;

/** Exact version-1 canonical snapshot/manifest encoding.
 *
 * Key ordering and trailing newline are part of the museum's Python fixture
 * parity and content-addressed SHA-256 contract. JSON is built from an
 * explicit public allowlist by the caller, never raw Eloquent attributes.
 */
final class MuseumSnapshotSerializer
{
    public function encode(array $content): string
    {
        $normalize = function ($value) use (&$normalize) {
            if (! is_array($value)) return $value;
            if (array_is_list($value)) return array_map($normalize, $value);
            ksort($value);
            return array_map($normalize, $value);
        };

        return json_encode(
            $normalize($content),
            JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES | JSON_THROW_ON_ERROR
        )."\n";
    }

    /** @param array<string, array{sha256: string, bytes: int}> $mediaFiles
     *  @param array<string, array{sha256: string, bytes: int}> $documentFiles
     */
    public function manifest(
        string $payload,
        array $mediaFiles,
        array $documentFiles,
        int $eventCount,
        int $entryCount,
        ?int $sectionCount
    ): string {
        $audit = [
            'schema_version' => 1,
            'files' => array_merge(
                ['published.json' => [
                    'sha256' => hash('sha256', $payload), 'bytes' => strlen($payload),
                ]],
                $mediaFiles, $documentFiles
            ),
            'event_count' => $eventCount,
            'entry_count' => $entryCount,
        ];
        if ($sectionCount !== null) $audit['section_count'] = $sectionCount;

        return $this->encode($audit);
    }
}
