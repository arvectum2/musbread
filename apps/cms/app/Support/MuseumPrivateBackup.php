<?php

declare(strict_types=1);

namespace App\Support;

use FilesystemIterator;
use RecursiveDirectoryIterator;
use RecursiveIteratorIterator;
use RuntimeException;
use SQLite3;
use ZipArchive;

/** TZ-088: no backups may enter the public static exporter or Git. */
final class MuseumPrivateBackup
{
    /** @return array{sha256:string,files:int,bytes:int} */
    public function create(string $databaseFile, string $privateStore, string $archive): array
    {
        if (! is_file($databaseFile) || is_link($databaseFile)) throw new RuntimeException('SQLite file missing or linked');
        if (file_exists($archive) || is_link($archive)) throw new RuntimeException('Refuse to overwrite existing backup');
        if (! is_dir(dirname($archive))) throw new RuntimeException('Backup directory must already exist');
        $temporaryDb = tempnam(dirname($archive), '.museum-backup-db-');
        if ($temporaryDb === false) throw new RuntimeException('Cannot stage consistent SQLite backup');
        $temporaryZip = tempnam(dirname($archive), '.museum-backup-zip-');
        if ($temporaryZip === false) { @unlink($temporaryDb); throw new RuntimeException('Cannot stage backup archive'); }
        chmod($temporaryDb, 0600); chmod($temporaryZip, 0600);
        try {
            $src = new SQLite3($databaseFile, SQLITE3_OPEN_READONLY);
            $dst = new SQLite3($temporaryDb, SQLITE3_OPEN_READWRITE | SQLITE3_OPEN_CREATE);
            try {
                if (! $src->backup($dst)) throw new RuntimeException('SQLite online backup failed');
                if ($dst->querySingle('PRAGMA integrity_check') !== 'ok') throw new RuntimeException('SQLite integrity check failed');
            } finally { $dst->close(); $src->close(); }
            $zip = new ZipArchive();
            if ($zip->open($temporaryZip, ZipArchive::CREATE | ZipArchive::OVERWRITE) !== true) {
                throw new RuntimeException('Cannot stage private ZIP');
            }
            $files = ['database.sqlite' => $temporaryDb];
            if (is_dir($privateStore)) {
                $root = rtrim($privateStore, "/");
                foreach (new RecursiveIteratorIterator(new RecursiveDirectoryIterator(
                    $privateStore, FilesystemIterator::SKIP_DOTS
                )) as $file) {
                    if ($file->isLink()) throw new RuntimeException('Private data contains symlink');
                    if (! $file->isFile()) continue;
                    $relative = substr($file->getPathname(), strlen($root) + 1);
                    if (str_contains($relative, "\\") || str_contains($relative, "\0")) throw new RuntimeException('Invalid private filename');
                    // Backups/restores do not recursively copy other backups.
                    if (str_starts_with($relative, 'backups/') || str_starts_with($relative, 'restores/')) continue;
                    $files['private/'.$relative] = $file->getPathname();
                }
            }
            ksort($files);
            $manifest = ['format' => 'musbread-private-backup-v1', 'files' => []];
            foreach ($files as $name => $source) {
                if (! $zip->addFile($source, $name)) throw new RuntimeException('Cannot add file to archive');
                $manifest['files'][$name] = ['sha256' => hash_file('sha256', $source), 'bytes' => filesize($source)];
            }
            if (! $zip->addFromString('manifest.json', json_encode($manifest, JSON_UNESCAPED_SLASHES | JSON_THROW_ON_ERROR))) {
                throw new RuntimeException('Cannot write backup manifest');
            }
            if (! $zip->close()) throw new RuntimeException('Cannot finalize backup ZIP');
            chmod($temporaryZip, 0600);
            // Atomic on the same private filesystem; original backup names immutable.
            if (! rename($temporaryZip, $archive)) throw new RuntimeException('Cannot finalize backup path');
            chmod($archive, 0600);
            return ['sha256' => hash_file('sha256', $archive), 'files' => count($files), 'bytes' => filesize($archive)];
        } finally { @unlink($temporaryDb); @unlink($temporaryZip); }
    }

    /** @return array{files:int,bytes:int} */
    public function verify(string $archive): array
    {
        if (! is_file($archive) || is_link($archive)) throw new RuntimeException('Backup archive missing or linked');
        $zip = new ZipArchive();
        if ($zip->open($archive, ZipArchive::RDONLY) !== true) throw new RuntimeException('Cannot open private archive');
        try {
            $manifestBytes = $zip->getFromName('manifest.json');
            if ($manifestBytes === false) throw new RuntimeException('Backup manifest missing');
            $manifest = json_decode($manifestBytes, true, flags: JSON_THROW_ON_ERROR);
            if (($manifest['format'] ?? '') !== 'musbread-private-backup-v1'
                || ! is_array($manifest['files'] ?? null)
                || ! array_key_exists('database.sqlite', $manifest['files'])) throw new RuntimeException('Unsupported backup format');
            $names = [];
            for ($i=0; $i<$zip->numFiles; ++$i) {
                $name = $zip->getNameIndex($i);
                if ($name === false || isset($names[$name])) throw new RuntimeException('Duplicate ZIP member');
                $names[$name] = true;
            }
            if (count($names) !== count($manifest['files']) + 1) throw new RuntimeException('Unexpected ZIP content');
            $bytes = 0;
            foreach ($manifest['files'] as $name => $meta) {
                if (! is_string($name) || ($name !== 'database.sqlite' && ! preg_match('#^private/(?!.*(?:^|/)\.\.?/)[a-zA-Z0-9_./-]+$#D', $name))
                    || str_contains($name, '..') || ! isset($names[$name])) throw new RuntimeException('Unsafe ZIP entry');
                $stream = $zip->getStream($name);
                if (! is_resource($stream)) throw new RuntimeException('Unreadable ZIP entry');
                $hash = hash_init('sha256'); $size = 0;
                try {
                    while (! feof($stream)) {
                        $chunk = fread($stream, 65536);
                        if ($chunk === false) throw new RuntimeException('Backup read failure');
                        hash_update($hash, $chunk); $size += strlen($chunk);
                    }
                } finally { fclose($stream); }
                if ($size !== ($meta['bytes'] ?? null) || ! hash_equals((string)($meta['sha256'] ?? ''), hash_final($hash))) {
                    throw new RuntimeException('Backup hash or length mismatch: '.$name);
                }
                $bytes += $size;
            }
            return ['files' => count($manifest['files']), 'bytes' => $bytes];
        } finally { $zip->close(); }
    }

    /** Restore only to a NEW isolated directory; never overwrite a running CMS. */
    public function restoreToNewDirectory(string $archive, string $directory): array
    {
        $report = $this->verify($archive);
        if (file_exists($directory) || is_link($directory)) throw new RuntimeException('Restore destination exists');
        if (! is_dir(dirname($directory))) throw new RuntimeException('Restore parent directory missing');
        $zip = new ZipArchive();
        if ($zip->open($archive, ZipArchive::RDONLY) !== true) throw new RuntimeException('Cannot open verified backup');
        $temp = dirname($directory).'/.restore-'.bin2hex(random_bytes(8));
        if (! mkdir($temp, 0700)) throw new RuntimeException('Cannot create private staging folder');
        try {
            $manifest = json_decode($zip->getFromName('manifest.json'), true, flags: JSON_THROW_ON_ERROR);
            foreach ($manifest['files'] as $name => $_) {
                $target = $temp.'/'.$name;
                if (! is_dir(dirname($target)) && ! mkdir(dirname($target), 0700, true)) {
                    throw new RuntimeException('Cannot create private restore subfolder');
                }
                $stream = $zip->getStream($name);
                $file = fopen($target, 'xb');
                if (! is_resource($file) || ! is_resource($stream)) throw new RuntimeException('Cannot restore private file');
                try { if (stream_copy_to_stream($stream, $file) === false) throw new RuntimeException('Restore copy failed'); }
                finally { fclose($stream); fclose($file); }
                chmod($target, 0600);
                if (filesize($target) !== $manifest['files'][$name]['bytes']
                    || ! hash_equals($manifest['files'][$name]['sha256'], hash_file('sha256', $target))) {
                    throw new RuntimeException('Restored file integrity mismatch');
                }
            }
            $db = new SQLite3($temp.'/database.sqlite', SQLITE3_OPEN_READONLY);
            try { if ($db->querySingle('PRAGMA integrity_check') !== 'ok') throw new RuntimeException('Restored database corrupt'); }
            finally { $db->close(); }
            if (! rename($temp, $directory)) throw new RuntimeException('Cannot finalize restore directory');
            return $report;
        } finally {
            $zip->close();
            if (is_dir($temp)) {
                $items = new RecursiveIteratorIterator(new RecursiveDirectoryIterator($temp, FilesystemIterator::SKIP_DOTS), RecursiveIteratorIterator::CHILD_FIRST);
                foreach ($items as $item) $item->isDir() ? rmdir($item->getPathname()) : unlink($item->getPathname());
                rmdir($temp);
            }
        }
    }
}
