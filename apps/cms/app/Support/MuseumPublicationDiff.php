<?php

declare(strict_types=1);

namespace App\Support;

use App\Models\MuseumSection;
use Illuminate\Support\Facades\Artisan;
use MoonShine\Laravel\Models\MoonshineUser;
use RuntimeException;

/** Preview the exact CMS export against a privately archived, verified local release. */
final class MuseumPublicationDiff
{
    private const LABELS = [
        'title' => 'Название', 'h1' => 'H1', 'slug' => 'URL', 'type' => 'Тип',
        'excerpt' => 'Анонс', 'body' => 'Основной текст', 'category' => 'Категория',
        'date' => 'Дата начала', 'ends_on' => 'Дата окончания', 'seo_title' => 'SEO-заголовок',
        'seo_description' => 'SEO-описание', 'parent_slug' => 'Родитель',
        'section_slug' => 'Раздел', 'sort_order' => 'Порядок',
        'media' => 'Изображения', 'documents' => 'Документы',
        'translations' => 'Переводы', 'related_entries' => 'Связанные материалы',
        'related_events' => 'Связанные события', 'legacy_path' => 'Исходный URL',
    ];

    /** @return array<string,mixed> */
    public function report(MoonshineUser $actor): array
    {
        $baseline = $this->loadBaseline();
        // No local baseline => do not pretend that all draft records are 'new'.
        $candidate = $this->candidate();
        $sectionSlugs = $actor->isSuperUser() ? null : MuseumSection::query()
            ->whereIn('id', MuseumSectionAccess::allowedIds($actor))
            ->pluck('slug')->all();

        $result = [
            'baseline_available' => $baseline !== null,
            'baseline_release' => $baseline['release'] ?? null,
            'baseline_sha256' => $baseline['sha256'] ?? null,
            'candidate_sha256' => $candidate['sha256'],
            'scope' => $actor->isSuperUser() ? 'all' : 'assigned',
            'summary' => ['added' => 0, 'changed' => 0, 'removed' => 0, 'unchanged' => 0],
            'groups' => [],
            'removed_urls' => [],
            'preflight' => app(MuseumContentPreflight::class)->report($actor),
        ];
        if ($baseline === null) return $result;

        foreach (['entries', 'events', 'sections', 'fixed_page_seo'] as $group) {
            // Section structure and fixed-route SEO are admin-only. Never
            // leak another editor's SEO changes in a scoped preview.
            if (in_array($group, ['sections', 'fixed_page_seo'], true)
                && ! $actor->isSuperUser()) continue;
            $oldData = $baseline['data'][$group] ?? [];
            $newData = $candidate['data'][$group] ?? [];
            if ($group === 'fixed_page_seo') {
                // Export intentionally keys these entries by public route.
                // Reuse the same semantic comparer with a stable slug.
                $convert = static fn (array $pages): array => collect($pages)
                    ->map(static fn (array $seo, string $path): array =>
                        ['slug' => $path, 'title' => $path] + $seo)->values()->all();
                $oldData = $convert($oldData);
                $newData = $convert($newData);
            }
            $old = $this->scope($oldData, $group, $sectionSlugs);
            $new = $this->scope($newData, $group, $sectionSlugs);
            $diff = $this->compare($old, $new, $group);
            $result['groups'][$group] = $diff;
            foreach ($diff as $row) {
                $result['summary'][$row['action']]++;
                if ($row['action'] === 'removed') {
                    foreach ($row['old_urls'] as $url) {
                        $result['removed_urls'][] = [
                            'path' => $url['path'], 'locale' => $url['locale'],
                            'kind' => $group, 'title' => $row['title'],
                        ];
                    }
                }
            }
        }
        usort($result['removed_urls'], static fn ($a, $b) => strcmp($a['path'], $b['path']));
        return $result;
    }

    /** @return array<string,mixed>|null */
    private function loadBaseline(): ?array
    {
        $root = rtrim((string) config('museum.local_release_root', base_path('../../deploy/local')), '/');
        $current = $root.'/current';
        if (! is_link($current)) return null;
        $releases = realpath($root.'/releases');
        $release = realpath($current);
        if ($releases === false || $release === false || dirname($release) !== $releases
            || ! preg_match('/^[a-f0-9]{16}$/D', basename($release))) return null;

        $manifestFile = $release.'/snapshot-manifest.json';
        $releaseFile = $release.'/release-manifest.json';
        if (! is_file($manifestFile) || is_link($manifestFile)
            || ! is_file($releaseFile) || is_link($releaseFile)) return null;
        $inventory = json_decode(file_get_contents($releaseFile), true);
        $manifestBytes = file_get_contents($manifestFile);
        // Re-authenticate the local release files against the immutable
        // release manifest; a stale/tampered current directory is not a base.
        $files = $inventory['files'] ?? null;
        if (($inventory['release'] ?? '') !== basename($release)
            || ! is_array($files) || ! isset($files['index.html'], $files['snapshot-manifest.json'])
            || $files['snapshot-manifest.json'] !== hash('sha256', $manifestBytes)) return null;
        $sorted = $files;
        ksort($sorted);
        if (substr(hash('sha256', json_encode($sorted, JSON_UNESCAPED_SLASHES | JSON_THROW_ON_ERROR)), 0, 16)
            !== basename($release)) return null;
        foreach ($files as $relative => $digest) {
            if (! is_string($relative) || str_starts_with($relative, '/')
                || str_contains($relative, '..') || str_contains($relative, chr(0))
                || ! preg_match('/^[a-f0-9]{64}$/D', (string) $digest)) return null;
            $file = $release.'/'.$relative;
            if (! is_file($file) || is_link($file) || hash_file('sha256', $file) !== $digest) return null;
        }
        $manifest = json_decode($manifestBytes, true);
        $meta = $manifest['files']['published.json'] ?? null;
        if (! is_array($meta) || ! preg_match('/^[a-f0-9]{64}$/D', (string) ($meta['sha256'] ?? ''))
            || ! is_int($meta['bytes'] ?? null)) return null;
        $sha = $meta['sha256'];
        $path = $root.'/private-snapshots/'.$sha.'.json';
        if (! is_file($path) || is_link($path)) return null;
        $bytes = file_get_contents($path);
        if ($bytes === false || strlen($bytes) !== $meta['bytes'] || hash('sha256', $bytes) !== $sha) return null;
        $data = json_decode($bytes, true);
        if (! is_array($data) || ($data['schema_version'] ?? null) !== 1
            || ! is_array($data['entries'] ?? null) || ! is_array($data['events'] ?? null)) return null;
        return ['data' => $data, 'sha256' => $sha, 'release' => basename($release)];
    }

    /** @return array{data:array<string,mixed>,sha256:string} */
    private function candidate(): array
    {
        // All outputs are isolated in OS temp, including exporter-generated
        // assets. No public files, CMS records, release pointers or queues change.
        $directory = sys_get_temp_dir().'/musbread-diff-'.bin2hex(random_bytes(12));
        if (! mkdir($directory, 0700)) throw new RuntimeException('Unable to create private preview directory');
        try {
            $output = $directory.'/published.json';
            $manifest = $directory.'/manifest.json';
            if (Artisan::call('museum:export', [
                '--output' => $output,
                '--manifest' => $manifest,
                '--media-output-dir' => $directory.'/media',
                '--document-output-dir' => $directory.'/documents',
            ]) !== 0) throw new RuntimeException('Private snapshot preview could not be generated');
            $bytes = file_get_contents($output);
            $audit = json_decode(file_get_contents($manifest), true, flags: JSON_THROW_ON_ERROR);
            if (hash('sha256', $bytes) !== ($audit['files']['published.json']['sha256'] ?? '')) {
                throw new RuntimeException('Private preview checksum mismatch');
            }
            return [
                'data' => json_decode($bytes, true, flags: JSON_THROW_ON_ERROR),
                'sha256' => hash('sha256', $bytes),
            ];
        } finally {
            // Only delete files we created inside our private random folder.
            $iterator = new \RecursiveIteratorIterator(
                new \RecursiveDirectoryIterator($directory, \FilesystemIterator::SKIP_DOTS),
                \RecursiveIteratorIterator::CHILD_FIRST);
            foreach ($iterator as $file) {
                if ($file->isDir() && ! $file->isLink()) rmdir($file->getPathname());
                else unlink($file->getPathname());
            }
            rmdir($directory);
        }
    }

    /** @param array<int,array<string,mixed>> $items
     *  @param list<string>|null $sections
     *  @return array<string,array<string,mixed>>
     */
    private function scope(array $items, string $group, ?array $sections): array
    {
        $result = [];
        foreach ($items as $item) {
            if ($sections !== null && in_array($group, ['entries', 'events'], true)
                && ! in_array($item['section_slug'] ?? null, $sections, true)) continue;
            $id = match ($group) {
                'entries' => ($item['type'] ?? '').':'.($item['slug'] ?? ''),
                default => $item['slug'] ?? '',
            };
            if ($id !== '') $result[$id] = $item;
        }
        ksort($result);
        return $result;
    }

    /** @param array<string,array<string,mixed>> $old
     *  @param array<string,array<string,mixed>> $new
     *  @return list<array<string,mixed>>
     */
    private function compare(array $old, array $new, string $group): array
    {
        $rows = [];
        foreach (array_unique(array_merge(array_keys($old), array_keys($new))) as $key) {
            $before = $old[$key] ?? null;
            $after = $new[$key] ?? null;
            $action = $before === null ? 'added' : ($after === null ? 'removed' : 'unchanged');
            $changes = [];
            if ($before !== null && $after !== null) {
                foreach (array_unique(array_merge(array_keys($before), array_keys($after))) as $field) {
                    if ($this->canonical($before[$field] ?? null) !== $this->canonical($after[$field] ?? null)) {
                        $changes[] = self::LABELS[$field] ?? $field;
                    }
                }
                if ($changes !== []) $action = 'changed';
            }
            $title = ($after ?? $before)['title'] ?? $key;
            $rows[] = [
                'key' => $key, 'title' => $title, 'action' => $action,
                'changed_fields' => $changes, 'kind' => $group,
                'type' => ($after ?? $before)['type'] ?? null,
                'slug' => ($after ?? $before)['slug'] ?? '',
                'old_urls' => $action === 'removed' ? $this->retiringPaths($group, $before) : [],
            ];
        }
        usort($rows, static fn ($a, $b) => strcmp($a['key'], $b['key']));
        return $rows;
    }

    /**
     * Public paths only. No redirect target is inferred, even for a slug
     * rename: editorial owners must decide whether a redirect is justified.
     * @param array<string,mixed> $before
     * @return list<array{path:string,locale:string}>
     */
    private function retiringPaths(string $group, array $before): array
    {
        $prefixes = [
            'page' => 'museum', 'news' => 'news', 'excursion' => 'excursions',
            'exhibition' => 'exhibitions', 'document' => 'documents',
        ];
        if ($group !== 'entries' && $group !== 'events') return [];
        $prefix = $group === 'events' ? 'events' : ($prefixes[$before['type'] ?? ''] ?? null);
        $slug = (string) ($before['slug'] ?? '');
        if ($prefix === null || preg_match('/^[a-z0-9]+(?:-[a-z0-9]+)*$/D', $slug) !== 1) return [];
        $path = '/'.$prefix.'/'.$slug.'/';
        $urls = [['path' => $path, 'locale' => 'ru']];
        if ($group === 'entries' && isset($before['translations']['en'])) {
            $urls[] = ['path' => '/en'.$path, 'locale' => 'en'];
        }
        return $urls;
    }

    private function canonical(mixed $value): string
    {
        if (is_array($value)) {
            if (array_is_list($value)) {
                $value = array_map(fn ($v) => json_decode($this->canonical($v), true), $value);
            } else {
                ksort($value);
                foreach ($value as $k => $v) $value[$k] = json_decode($this->canonical($v), true);
            }
        }
        return json_encode($value, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES | JSON_THROW_ON_ERROR);
    }
}
