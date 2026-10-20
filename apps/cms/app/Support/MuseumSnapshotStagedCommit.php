<?php

declare(strict_types=1);

namespace App\Support;

use FilesystemIterator;
use RecursiveDirectoryIterator;
use RecursiveIteratorIterator;
use RuntimeException;
use Throwable;

/**
 * Private preparation, then rollback-capable direct-export promotion.
 *
 * This preserves the existing museum:export CLI outputs. Each individual
 * file is renamed atomically; multiple destinations are NOT a globally atomic
 * release. The separate immutable-release/current-symlink deployment remains
 * the only appropriate final website switch.
 */
final class MuseumSnapshotStagedCommit
{
    public function begin(): string
    {
        // Staging is private CMS storage on ArvectumSSD, not Next.js public/.
        $parent = storage_path('app/private/museum-export-stages');
        if (is_link($parent)) throw new RuntimeException('Unsafe staged export directory');
        if (! is_dir($parent) && ! mkdir($parent, 0700, true) && ! is_dir($parent)) {
            throw new RuntimeException('Cannot create private export staging root');
        }
        if (! is_dir($parent) || is_link($parent)) {
            throw new RuntimeException('Unsafe staged export root');
        }
        $stage = $parent.'/stage-'.bin2hex(random_bytes(12));
        if (! mkdir($stage, 0700)) throw new RuntimeException('Cannot create private export stage');
        return $stage;
    }

    public function cleanup(string $stage): void
    {
        // Refuse traversal/out-of-scope cleanup. Never follow symlinks.
        $parent = realpath(storage_path('app/private/museum-export-stages'));
        if ($parent === false || ! preg_match('~^'.preg_quote($parent, '~').'/stage-[a-f0-9]{24}$~D', $stage)
            || is_link($stage)) {
            throw new RuntimeException('Unsafe staged export cleanup path');
        }
        if (! is_dir($stage)) return;
        $iterator = new RecursiveIteratorIterator(
            new RecursiveDirectoryIterator($stage, FilesystemIterator::SKIP_DOTS),
            RecursiveIteratorIterator::CHILD_FIRST
        );
        foreach ($iterator as $file) {
            if ($file->isDir() && ! $file->isLink()) rmdir($file->getPathname());
            else unlink($file->getPathname());
        }
        rmdir($stage);
    }

    /**
     * Precondition: all CMS checks AND final approval-set recheck succeeded.
     * All declared stage files are rehashed before touching any destination.
     * Roll back ordinary write/rename failures, including withdrawn assets.
     *
     * @param array<string,array{sha256:string,bytes:int}> $mediaFiles
     * @param array<string,array{sha256:string,bytes:int}> $documentFiles
     * @param null|callable(string):void $checkpoint For injected test failures.
     */
    public function commit(
        string $stage,
        string $output,
        string $manifest,
        string $mediaDir,
        string $documentDir,
        array $mediaFiles,
        array $documentFiles,
        ?callable $checkpoint = null
    ): void {
        $this->assertStage($stage);
        if ($output === $manifest || $mediaDir === $documentDir
            || str_contains($output, chr(0)) || str_contains($manifest, chr(0))) {
            throw new RuntimeException('Unsafe overlapping export targets');
        }

        $files = [
            [$stage.'/published.json', $output],
            [$stage.'/snapshot-manifest.json', $manifest],
        ];
        foreach ([['media', $mediaDir, $mediaFiles], ['documents', $documentDir, $documentFiles]]
            as [$prefix, $dir, $declared]) {
            foreach ($declared as $name => $meta) {
                if (! is_string($name) || ! $this->allowedName($prefix, $name)
                    || ! preg_match('/^[a-f0-9]{64}$/D', (string) ($meta['sha256'] ?? ''))
                    || ! is_int($meta['bytes'] ?? null) || $meta['bytes'] < 0) {
                    throw new RuntimeException('Unsafe static asset declaration');
                }
                $base = basename($name);
                $source = $stage.'/'.$prefix.'/'.$base;
                if (! is_file($source) || is_link($source)
                    || filesize($source) !== $meta['bytes']
                    || hash_file('sha256', $source) !== $meta['sha256']) {
                    throw new RuntimeException('Prepared file failed integrity verification');
                }
                $files[] = [$source, rtrim($dir, '/').'/'.$base];
            }
        }

        $payload = file_get_contents($stage.'/published.json');
        $auditBytes = file_get_contents($stage.'/snapshot-manifest.json');
        if ($payload === false || $auditBytes === false) throw new RuntimeException('Missing staged JSON');
        $audit = json_decode($auditBytes, true, 512, JSON_THROW_ON_ERROR);
        if (($audit['files']['published.json']['sha256'] ?? null) !== hash('sha256', $payload)
            || ($audit['files']['published.json']['bytes'] ?? null) !== strlen($payload)
            || ! is_array($audit['files'] ?? null)
            || count($audit['files']) !== count($mediaFiles) + count($documentFiles) + 1) {
            throw new RuntimeException('Staged manifest does not match snapshot');
        }
        foreach ($mediaFiles + $documentFiles as $name => $meta) {
            $record = $audit['files'][$name] ?? null;
            if (! is_array($record) || count($record) !== 2
                || ($record['sha256'] ?? null) !== $meta['sha256']
                || ($record['bytes'] ?? null) !== $meta['bytes']) {
                throw new RuntimeException('Staged manifest asset mismatch');
            }
        }

        // Guard all targets before mutating anything. A symlink as a final
        // file/ancestor must never redirect this command into private storage.
        $destinations = array_column($files, 1);
        if (count(array_unique($destinations)) !== count($destinations)) {
            throw new RuntimeException('Overlapping export file destinations');
        }
        foreach ($files as [, $target]) $this->assertTarget($target);

        $withdraw = [];
        foreach ([['media', $mediaDir, $mediaFiles, '/^[a-f0-9]{64}\.webp$/D'],
                  ['documents', $documentDir, $documentFiles, '/^[a-f0-9]{64}\.(?:pdf|docx|xlsx)$/D']]
            as [$prefix, $dir, $declared, $pattern]) {
            if (! is_dir($dir)) continue;
            foreach (glob(rtrim($dir, '/').'/*') ?: [] as $existing) {
                if (preg_match($pattern, basename($existing))
                    && ! array_key_exists($prefix.'/'.basename($existing), $declared)) {
                    $this->assertTarget($existing);
                    if (is_file($existing)) $withdraw[] = $existing;
                }
            }
        }

        // A complete backup is written BEFORE each destination is touched.
        // The first two JSON files are applied last, after assets exist.
        $ordered = array_merge(array_slice($files, 2), [$files[1], $files[0]]);
        $journal = [];
        try {
            foreach ($ordered as [$from, $to]) {
                $this->swapPreparedFile($from, $to, $stage, $journal);
                if ($checkpoint !== null) $checkpoint('after-write');
            }
            foreach ($withdraw as $target) {
                $this->backup($target, $stage, $journal);
                if (! unlink($target)) throw new RuntimeException('Cannot withdraw obsolete asset');
                if ($checkpoint !== null) $checkpoint('after-withdraw');
            }
        } catch (Throwable $error) {
            $failedRestore = false;
            foreach (array_reverse($journal) as [$destination, $backup]) {
                try {
                    if ($backup === null) {
                        if (is_file($destination) && ! unlink($destination)) {
                            throw new RuntimeException('Cannot remove partial new asset');
                        }
                    } else {
                        $this->replaceFile($backup, $destination);
                    }
                } catch (Throwable) {
                    $failedRestore = true;
                }
            }
            if ($failedRestore) {
                throw new RuntimeException('Export failed and rollback was incomplete', 0, $error);
            }
            throw $error;
        }
    }

    private function assertStage(string $stage): void
    {
        $parent = realpath(storage_path('app/private/museum-export-stages'));
        if ($parent === false || dirname($stage) !== $parent
            || ! preg_match('/^stage-[a-f0-9]{24}$/D', basename($stage))
            || ! is_dir($stage) || is_link($stage) || realpath($stage) !== $stage) {
            throw new RuntimeException('Unsafe private export stage');
        }
    }

    private function allowedName(string $prefix, string $name): bool
    {
        $extension = $prefix === 'media' ? 'webp' : '(?:pdf|docx|xlsx)';
        return (bool) preg_match('~^'.preg_quote($prefix, '~').'/[a-f0-9]{64}\.'.$extension.'$~D', $name);
    }

    private function assertTarget(string $target): void
    {
        if ($target === '' || ! str_starts_with($target, '/')
            || str_contains($target, chr(0))) {
            throw new RuntimeException('Unsafe export destination');
        }
        // Inspect EVERY ancestor, not only the nearest existing directory:
        // /output/link/subfolder would otherwise follow a symlink to private CMS.
        $parts = explode('/', trim($target, '/'));
        if (in_array('', $parts, true) || in_array('.', $parts, true)
            || in_array('..', $parts, true)) {
            throw new RuntimeException('Unsafe export destination');
        }
        $current = '';
        foreach ($parts as $part) {
            $current .= '/'.$part;
            if (is_link($current)) {
                // macOS uses /var -> /private/var for legitimate OS temp
                // directories. Reject every other parent symlink.
                $macTempAlias = PHP_OS_FAMILY === 'Darwin'
                    && $current === '/var' && realpath('/var') === '/private/var';
                if (! $macTempAlias) {
                    throw new RuntimeException('Unsafe export destination');
                }
            }
            if (file_exists($current) && $current !== $target && ! is_dir($current)) {
                throw new RuntimeException('Non-directory export ancestor');
            }
        }
        if (file_exists($target) && ! is_file($target)) {
            throw new RuntimeException('Export target is not a regular file');
        }
    }

    private function backup(string $target, string $stage, array &$journal): void
    {
        $backup = null;
        if (is_file($target)) {
            $backup = $stage.'/backup-'.bin2hex(random_bytes(10));
            if (! copy($target, $backup)
                || filesize($target) !== filesize($backup)
                || hash_file('sha256', $target) !== hash_file('sha256', $backup)) {
                throw new RuntimeException('Cannot verify export rollback backup');
            }
        }
        $journal[] = [$target, $backup];
    }

    private function swapPreparedFile(string $from, string $to, string $stage, array &$journal): void
    {
        $this->assertTarget($to);
        if (! is_dir(dirname($to)) && ! mkdir(dirname($to), 0755, true) && ! is_dir(dirname($to))) {
            throw new RuntimeException('Cannot create export directory');
        }
        if (is_file($to) && hash_file('sha256', $to) === hash_file('sha256', $from)) {
            return; // Keep byte-identical output inode stable.
        }
        $this->backup($to, $stage, $journal);
        $this->replaceFile($from, $to);
    }

    private function replaceFile(string $from, string $to): void
    {
        $temporary = $to.'.musbread-tmp-'.bin2hex(random_bytes(9));
        try {
            if (! copy($from, $temporary)
                || filesize($from) !== filesize($temporary)
                || hash_file('sha256', $from) !== hash_file('sha256', $temporary)
                || ! rename($temporary, $to)) {
                throw new RuntimeException('Cannot atomically replace prepared export file');
            }
        } finally {
            if (is_file($temporary)) unlink($temporary);
        }
    }
}
