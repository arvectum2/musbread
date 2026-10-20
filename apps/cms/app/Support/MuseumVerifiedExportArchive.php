<?php

declare(strict_types=1);

namespace App\Support;

use App\Models\MuseumExportContentProof;
use App\Models\MuseumPublicationRun;
use FilesystemIterator;
use RecursiveDirectoryIterator;
use RecursiveIteratorIterator;
use RuntimeException;
use Throwable;

/**
 * Optional and private: archive the exact bytes already checked by the
 * explicit-approval exporter. No public deploy, no CMS object rewriting.
 *
 * Content-addressed, single writer (flock), staged and atomically published.
 * 0440 files are advisory, NOT OS-enforced WORM or protection from the owner.
 */
final class MuseumVerifiedExportArchive
{
    public function archive(
        MuseumPublicationRun $run,
        string $snapshot,
        string $manifestPath,
        string $mediaDir,
        string $documentDir
    ): ?array {
        $configured = config('museum.verified_archive_root');
        if ($configured === null || $configured === '') return null;
        if (! config('museum.editorial_approval_queue')
            || $run->content_verified_at === null
            || $run->manifest_sha256 === null
            || $run->snapshot_sha256 === null
            || $run->content_proof_count === null) {
            throw new RuntimeException('Archive requires previously verified explicit approvals');
        }

        $root = $this->root($configured);
        if (is_link($root.'/.archive.lock')) {
            throw new RuntimeException('Unsafe symlink archive lock');
        }
        $lock = fopen($root.'/.archive.lock', 'c');
        if (! is_resource($lock)) throw new RuntimeException('Cannot open private archive lock');
        chmod($root.'/.archive.lock', 0600);
        try {
            if (! flock($lock, LOCK_EX)) throw new RuntimeException('Cannot lock private archive');
            return $this->createLocked($root, $run, $snapshot, $manifestPath, $mediaDir, $documentDir);
        } finally {
            flock($lock, LOCK_UN);
            fclose($lock);
        }
    }

    private function root(mixed $candidate): string
    {
        if (! is_string($candidate) || ! str_starts_with($candidate, '/')
            || str_contains($candidate, "\0") || str_contains($candidate, '//')
            || preg_match('~/(?:\.|\.\.)(?:/|$)~', $candidate)) {
            throw new RuntimeException('Unsafe private archive root');
        }
        $candidate = rtrim($candidate, '/');
        // Operator MUST provision the path; don't silently create it inside
        // public/, sources, a symlink, or someone's unrelated file tree.
        if (! is_dir($candidate) || is_link($candidate)
            || ($root = realpath($candidate)) === false || $root !== $candidate
            || $root === '/') {
            throw new RuntimeException('Private archive root must exist as a real directory');
        }
        // Receipt contains private approval IDs and potentially museum
        // documents. Refuse an operator's accidentally world-readable root.
        if ((fileperms($root) & 0077) !== 0) {
            throw new RuntimeException('Private archive root requires owner-only permissions (0700)');
        }
        foreach (array_filter([
            realpath(public_path()), realpath(base_path('../web/public')),
            realpath(base_path('../web/src')), realpath(base_path('app')),
            realpath(base_path('resources')),
        ]) as $excluded) {
            if ($root === $excluded || str_starts_with($root, $excluded.'/')) {
                throw new RuntimeException('Private archive root overlaps application or public files');
            }
        }
        $parts = explode('/', trim($root,'/'));
        $next = '';
        foreach ($parts as $part) {
            $next .= '/'.$part;
            if (is_link($next)) throw new RuntimeException('Private archive root has a symlink ancestor');
        }
        return $root;
    }

    private function createLocked(
        string $root, MuseumPublicationRun $run, string $snapshot, string $manifestPath,
        string $mediaDir, string $documentDir
    ): array {
        $manifestRaw = $this->readRegular($manifestPath);
        $snapshotRaw = $this->readRegular($snapshot);
        $snapshotHash = hash('sha256', $snapshotRaw);
        $manifestHash = hash('sha256', $manifestRaw);
        if ($snapshotHash !== $run->snapshot_sha256
            || $manifestHash !== $run->manifest_sha256) {
            throw new RuntimeException('Verified run hash changed before archive');
        }
        $manifest = json_decode($manifestRaw, true, 512, JSON_THROW_ON_ERROR);
        $payload = json_decode($snapshotRaw, true, 512, JSON_THROW_ON_ERROR);
        if (! is_array($manifest) || ($manifest['schema_version'] ?? null) !== 1
            || ! is_array($payload) || ($payload['schema_version'] ?? null) !== 1
            || ! is_array($manifest['files'] ?? null)
            || count($manifest['files']) > 5000
            || ($manifest['files']['published.json']['sha256'] ?? null) !== $snapshotHash
            || ($manifest['files']['published.json']['bytes'] ?? null) !== strlen($snapshotRaw)) {
            throw new RuntimeException('Malformed verified source archive manifest');
        }

        // A different approved run may legitimately export identical bytes.
        // Each run gets its own write-once attestation with its own approval IDs.
        $id = 'run-'.$run->id.'-'.$snapshotHash.'-'.$manifestHash;
        $final = $root.'/'.$id;
        if (file_exists($final) || is_link($final)) {
            throw new RuntimeException('Existing archive must never be replaced (verify it separately)');
        }
        $stage = $root.'/.stage-'.bin2hex(random_bytes(12));
        if (! mkdir($stage, 0700)) throw new RuntimeException('Cannot stage private archive');
        try {
            $files = [];
            foreach ($manifest['files'] as $name => $meta) {
                if (! is_array($meta)
                    || count($meta) !== 2
                    || ! preg_match('~^(?:published\.json|media/[a-f0-9]{64}\.webp|documents/[a-f0-9]{64}\.(?:pdf|docx|xlsx))$~D', (string) $name)
                    || ! preg_match('/^[a-f0-9]{64}$/D', (string) ($meta['sha256'] ?? ''))
                    || ! is_int($meta['bytes'] ?? null) || $meta['bytes'] < 0) {
                    throw new RuntimeException('Unsafe declared archive file');
                }
                $source = match (true) {
                    $name === 'published.json' => $snapshot,
                    str_starts_with($name, 'media/') => rtrim($mediaDir, '/').'/'.basename($name),
                    default => rtrim($documentDir, '/').'/'.basename($name),
                };
                $this->copyValidated($source, $stage.'/'.$name, $meta['sha256'], $meta['bytes']);
                $files[$name] = $meta;
            }
            $this->copyValidated(
                $manifestPath, $stage.'/snapshot-manifest.json',
                $manifestHash, strlen($manifestRaw)
            );
            $files['snapshot-manifest.json'] = [
                'sha256'=>$manifestHash, 'bytes'=>strlen($manifestRaw),
            ];
            ksort($files);
            $proofs = MuseumExportContentProof::query()
                ->where('publication_run_id', $run->id)
                ->orderBy('subject_kind')->orderBy('subject_id')->get();
            $records = [];
            foreach (['entry'=>'entries','event'=>'events','section'=>'sections'] as $kind=>$group) {
                if (! is_array($payload[$group] ?? [])) {
                    throw new RuntimeException('Invalid archive subject list');
                }
                foreach ($payload[$group] ?? [] as $row) {
                    if (! is_array($row)) throw new RuntimeException('Invalid archive subject');
                    $identity = $kind === 'entry'
                        ? ($row['type'] ?? '').':'.($row['slug'] ?? '')
                        : ($row['slug'] ?? '');
                    $records[$kind.'|'.$identity] = hash(
                        'sha256', app(MuseumSnapshotSerializer::class)->encode($row)
                    );
                }
            }
            if ($proofs->count() !== $run->content_proof_count
                || $proofs->count() !== count($records)) {
                throw new RuntimeException('Archive subject and proof counts differ');
            }
            $receiptProofs = [];
            foreach ($proofs as $proof) {
                $kind = $proof->subject_kind;
                if (! in_array($kind, ['entry','event','section'], true)
                    || $proof->snapshot_sha256 !== $snapshotHash
                    || ! preg_match('/^[a-f0-9]{64}$/D', $proof->revision_sha256)
                    || ! preg_match('/^[a-f0-9]{64}$/D', $proof->export_record_sha256)) {
                    throw new RuntimeException('Unsafe archive proof record');
                }
                $matching = array_keys(array_filter(
                    $records,
                    static fn (string $hash): bool => hash_equals($hash, $proof->export_record_sha256)
                ));
                $matching = array_values(array_filter(
                    $matching, static fn (string $key): bool => str_starts_with($key, $kind.'|')
                ));
                if (count($matching) !== 1) {
                    throw new RuntimeException('Archive cannot identify exactly one approved row');
                }
                $identity = substr($matching[0], strlen($kind)+1);
                unset($records[$matching[0]]);
                $receiptProofs[] = [
                    'kind'=>$kind, 'identity'=>$identity, 'subject_id'=>$proof->subject_id,
                    'approval_id'=>$proof->approval_id,
                    'revision_sha256'=>$proof->revision_sha256,
                    'export_record_sha256'=>$proof->export_record_sha256,
                ];
            }
            if ($records !== []) throw new RuntimeException('Archive contains unproven content records');
            $receipt = [
                'schema_version'=>1,
                'publication_run_id'=>$run->id,
                'snapshot_sha256'=>$snapshotHash,
                'manifest_sha256'=>$manifestHash,
                'files'=>$files,
                'proofs'=>$receiptProofs,
            ];
            $encoded = app(MuseumSnapshotSerializer::class)->encode($receipt);
            $this->writeNew($stage.'/archive-receipt.json', $encoded);
            // Recheck staged bytes before publishing; never expose partial archive.
            foreach ($files as $name=>$meta) {
                if (! is_file($stage.'/'.$name) || is_link($stage.'/'.$name)
                    || filesize($stage.'/'.$name) !== $meta['bytes']
                    || hash_file('sha256', $stage.'/'.$name) !== $meta['sha256']) {
                    throw new RuntimeException('Archive stage verification failed');
                }
            }
            $this->makeReadOnly($stage);
            // Under flock, destination is still absent; atomic rename of
            // completed staging directory is the sole publication step.
            if (file_exists($final) || is_link($final) || ! rename($stage, $final)) {
                throw new RuntimeException('Archive destination became occupied');
            }
            return [
                'archive_id'=>$id,
                'archive_receipt_sha256'=>hash('sha256', $encoded),
                'archive_file_count'=>count($files),
            ];
        } finally {
            if (is_dir($stage) && ! is_link($stage)) {
                $this->removeStage($stage);
            }
        }
    }

    private function readRegular(string $source): string
    {
        if (! is_file($source) || is_link($source)) {
            throw new RuntimeException('Archive source must be a regular file');
        }
        $bytes = file_get_contents($source);
        if (! is_string($bytes)) throw new RuntimeException('Unable to read archive source');
        return $bytes;
    }

    private function copyValidated(string $source, string $destination, string $hash, int $length): void
    {
        if (! is_file($source) || is_link($source)
            || filesize($source) !== $length || hash_file('sha256', $source) !== $hash) {
            throw new RuntimeException('Changed, symlinked or missing archive source');
        }
        $dir = dirname($destination);
        if (! is_dir($dir) && ! mkdir($dir, 0700, true) && ! is_dir($dir)) {
            throw new RuntimeException('Cannot create private archive subdirectory');
        }
        if (! copy($source, $destination)
            || filesize($destination) !== $length
            || hash_file('sha256', $destination) !== $hash) {
            throw new RuntimeException('Archive copy failed checksum verification');
        }
        chmod($destination, 0440);
    }

    private function writeNew(string $path, string $data): void
    {
        $handle = fopen($path, 'x');
        if (! is_resource($handle)) throw new RuntimeException('Cannot create archive receipt');
        try {
            if (fwrite($handle, $data) !== strlen($data)) {
                throw new RuntimeException('Cannot write archive receipt');
            }
            fflush($handle);
            if (function_exists('fsync') && ! fsync($handle)) {
                throw new RuntimeException('Cannot flush archive receipt');
            }
        } finally {
            fclose($handle);
        }
        chmod($path, 0440);
    }

    private function makeReadOnly(string $stage): void
    {
        foreach (['media','documents'] as $name) {
            if (is_dir($stage.'/'.$name)) chmod($stage.'/'.$name, 0500);
        }
        chmod($stage, 0500);
    }

    private function removeStage(string $stage): void
    {
        $iterator = new RecursiveIteratorIterator(
            new RecursiveDirectoryIterator($stage, FilesystemIterator::SKIP_DOTS),
            RecursiveIteratorIterator::CHILD_FIRST
        );
        foreach ($iterator as $item) {
            if ($item->isLink()) throw new RuntimeException('Archive stage symlink discovered');
            if ($item->isDir()) {
                chmod($item->getPathname(), 0700);
                rmdir($item->getPathname());
            } else unlink($item->getPathname());
        }
        chmod($stage, 0700);
        rmdir($stage);
    }
}
