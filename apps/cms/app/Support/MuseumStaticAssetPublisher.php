<?php

declare(strict_types=1);

namespace App\Support;

use App\Models\MuseumEntry;
use Illuminate\Support\Facades\Storage;

/** The only public static-asset filesystem boundary of museum:export.
 *
 * Preserve source SHA/format validation and content-addressed output names.
 * Private CMS drafts and rights-pending files must never enter these folders.
 * These methods are called ONLY after the command's approval/preflight gates.
 */
final class MuseumStaticAssetPublisher
{
    /** @param array<string, array{sha256: string, bytes: int}> $mediaFiles */
    public function publishImages(MuseumEntry $entry, string $mediaDir, array &$mediaFiles): array
    {
        $images = [];
        foreach ($entry->media as $image) {
            // Original museum source photos are copied ONLY into the
            // private CMS until rights/alt and eventual release are
            // explicitly reviewed. Publishing the parent entry alone
            // must never leak a source-restricted photo.
            if ($image->source_rights_pending) continue;
            // Also protect older records inserted before the new
            // upload policy. Never export a non-compliant public alt.
            if ($issue = MuseumAltPolicy::issue($image->alt)) {
                throw new \RuntimeException('Public media alt policy failed; fix in private CMS: '.$image->id);
            }
            $raw = Storage::disk('local')->get($image->storage_path);
            if (! is_string($raw) || hash('sha256', $raw) !== $image->sha256
                || strlen($raw) !== $image->size_bytes
                || (@getimagesizefromstring($raw)[2] ?? null) !== IMAGETYPE_WEBP) {
                throw new \RuntimeException('Uploaded image checksum or format invalid: '.$image->id);
            }
            if (! is_dir($mediaDir) && ! mkdir($mediaDir, 0755, true) && ! is_dir($mediaDir)) {
                throw new \RuntimeException('Cannot create public media directory');
            }
            if (! preg_match('/^[a-f0-9]{64}$/D', $image->sha256)) {
                throw new \RuntimeException('Invalid image digest');
            }
            $target = rtrim($mediaDir, '/').'/'.$image->sha256.'.webp';
            if (! is_file($target) || hash_file('sha256', $target) !== $image->sha256) {
                $tmp = $target.'.tmp.'.getmypid();
                if (file_put_contents($tmp, $raw, LOCK_EX) === false || ! rename($tmp, $target)) {
                    throw new \RuntimeException('Cannot publish media file');
                }
            }
            $mediaFiles['media/'.$image->sha256.'.webp'] = [
                'sha256' => $image->sha256, 'bytes' => $image->size_bytes,
            ];
            $images[] = [
                'src' => '/media/'.$image->sha256.'.webp',
                'alt' => $image->alt, 'caption' => $image->caption,
                ...($image->long_description !== null && trim($image->long_description) !== ''
                    ? ['long_description' => $image->long_description] : []),
                'width' => $image->width, 'height' => $image->height,
            ];
        }
        return $images;
    }

    /** @param array<string, array{sha256: string, bytes: int}> $documentFiles */
    public function publishDocuments(
        MuseumEntry $entry,
        string $documentDir,
        MuseumDocumentInspector $inspector,
        array &$documentFiles
    ): array {
        $documents = [];
        foreach ($entry->documents as $document) {
            $path = Storage::disk('local')->path($document->storage_path);
            if (! is_file($path) || hash_file('sha256', $path) !== $document->sha256
                || filesize($path) !== $document->size_bytes
                || ! in_array($document->file_type, ['pdf', 'docx', 'xlsx'], true)) {
                throw new \RuntimeException('Document checksum or format invalid: '.$document->id);
            }
            $inspector->verify($path, $document->file_type);
            if (! preg_match('/^[a-f0-9]{64}$/D', $document->sha256)) {
                throw new \RuntimeException('Invalid document digest');
            }
            if (! is_dir($documentDir) && ! mkdir($documentDir, 0755, true) && ! is_dir($documentDir)) {
                throw new \RuntimeException('Cannot create static document directory');
            }
            $name = $document->sha256.'.'.$document->file_type;
            $target = rtrim($documentDir, '/').'/'.$name;
            if (! is_file($target) || hash_file('sha256', $target) !== $document->sha256) {
                $temp = $target.'.tmp.'.getmypid();
                if (! copy($path, $temp) || ! rename($temp, $target)) {
                    throw new \RuntimeException('Cannot publish document');
                }
            }
            $documentFiles['documents/'.$name] = [
                'sha256' => $document->sha256, 'bytes' => $document->size_bytes,
            ];
            $documents[] = [
                'href' => '/documents/'.$name,
                'label' => $document->label,
                'format' => $document->file_type,
                'size_bytes' => $document->size_bytes,
                'accessibility_reviewed' => $document->accessibility_reviewed,
                // Unreviewed editorial notes must never leak to the public JSON.
                'accessibility_note' => $document->accessibility_reviewed
                    ? $document->accessibility_note : null,
                // Distinct full-text HTML, published only after human
                // equivalence attestation and immutable hash binding.
                ...($document->accessible_edition_sha256 !== null
                    ? ['accessible_html'=>$document->accessible_html] : []),
            ];
        }
        return $documents;
    }

    /** Only generated export folders may be passed, never CMS private storage.
     *  Withdraw files no longer approved without touching unrelated documents.
     *
     * @param array<string, array{sha256: string, bytes: int}> $mediaFiles
     * @param array<string, array{sha256: string, bytes: int}> $documentFiles
     */
    public function pruneWithdrawn(
        string $mediaDir, string $documentDir, array $mediaFiles, array $documentFiles
    ): void {
        // Prune assets withdrawn by the editor from this *generated-only* folder.
        // Otherwise a formerly published image would remain publicly accessible.
        if (is_dir($mediaDir)) {
            foreach (glob(rtrim($mediaDir, '/').'/*.webp') ?: [] as $existing) {
                // This folder may contain non-exported operator files.
                // Only our SHA-named generated WebP files can be withdrawn.
                if (is_file($existing)
                    && preg_match('/^[a-f0-9]{64}\.webp$/D', basename($existing))
                    && ! array_key_exists('media/'.basename($existing), $mediaFiles)) {
                    unlink($existing);
                }
            }
        }

        // Withdraw generated documents removed by the editor or hidden by draft status.
        // Never touch arbitrary files beyond the content-addressed export directory.
        if (is_dir($documentDir)) {
            foreach (glob(rtrim($documentDir, '/').'/*') ?: [] as $existing) {
                if (is_file($existing)
                    && preg_match('/^[a-f0-9]{64}\\.(?:pdf|docx|xlsx)$/D', basename($existing))
                    && ! array_key_exists('documents/'.basename($existing), $documentFiles)) {
                    unlink($existing);
                }
            }
        }
    }
}
