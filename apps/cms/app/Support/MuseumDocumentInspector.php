<?php

namespace App\Support;

use Illuminate\Validation\ValidationException;
use ZipArchive;

/**
 * Closed-world signature and structure validator. No extraction, macros or
 * inline document rendering. AV/CDR of customer files is a separate gate.
 */
final class MuseumDocumentInspector
{
    public const EXTENSIONS = ['pdf', 'docx', 'xlsx'];
    public const MAX_BYTES = 15 * 1024 * 1024;

    public function verify(string $path, string $extension): void
    {
        $extension = strtolower($extension);
        if (! in_array($extension, self::EXTENSIONS, true)) {
            $this->invalid();
        }
        $size = filesize($path);
        if ($size === false || $size < 16 || $size > self::MAX_BYTES) {
            $this->invalid();
        }

        $handle = fopen($path, 'rb');
        if ($handle === false) $this->invalid();
        $header = fread($handle, 16);
        fclose($handle);

        if ($extension === 'pdf') {
            $pdf = file_get_contents($path);
            if (! is_string($pdf)) $this->invalid();
            $this->verifyPdfBytes($pdf, (string) mime_content_type($path));
            return;
        }

        if ($extension === 'xls') {
            if (! str_starts_with($header, "\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1")) $this->invalid();
            // Legacy OLE2 can contain macros and embeds. Accept only after
            // a separate virus-scanning pipeline is approved by the museum.
            $this->invalid();
        }

        if (! str_starts_with($header, "PK\x03\x04")) $this->invalid();
        $zip = new ZipArchive();
        if ($zip->open($path, ZipArchive::RDONLY) !== true) $this->invalid();
        try {
            if ($zip->numFiles < 2 || $zip->numFiles > 600) $this->invalid();
            $expected = $extension === 'docx' ? 'word/document.xml' : 'xl/workbook.xml';
            if ($zip->locateName('[Content_Types].xml') === false ||
                $zip->locateName($expected) === false) $this->invalid();

            $inflated = 0;
            for ($i = 0; $i < $zip->numFiles; $i++) {
                $stat = $zip->statIndex($i);
                if (! is_array($stat)) $this->invalid();
                $name = $stat['name'];
                if (str_contains($name, '..') || str_starts_with($name, '/') ||
                    str_contains($name, '\\') || str_contains($name, "\0")) $this->invalid();
                if (preg_match('#(?:vbaProject|activeX|embeddings|externalLinks|oleObject|\\.bin$)#i', $name)) {
                    $this->invalid();
                }
                $bytes = (int) $stat['size'];
                $packed = (int) $stat['comp_size'];
                if ($bytes > 20 * 1024 * 1024 || ($packed > 0 && $bytes > 200 * $packed)) {
                    $this->invalid();
                }
                $inflated += $bytes;
                if ($inflated > 40 * 1024 * 1024) $this->invalid();
            }
            $types = $zip->getFromName('[Content_Types].xml');
            if (! is_string($types) || strlen($types) > 300000 ||
                preg_match('#(?:macroEnabled|vbaProject|activex|oleObject|externalLink)#i', $types)) {
                $this->invalid();
            }
        } finally {
            $zip->close();
        }
    }

    /**
     * Validate the exact immutable byte snapshot that will be returned in an
     * authenticated download, not a source path that can change afterwards.
     * ZipArchive/mime_content_type require a private file; it exists only
     * during this check, under the CMS framework storage on ArvectumSSD.
     */
    public function verifyBytes(string $bytes, string $extension): void
    {
        if (strlen($bytes) < 16 || strlen($bytes) > self::MAX_BYTES) {
            $this->invalid();
        }
        // The PDF is ALREADY held in the approved HTTP response buffer.
        // Re-reading it and writing another 15 MiB copy to storage adds
        // latency and memory without improving the security gate.
        if (strtolower($extension) === 'pdf') {
            $mime = (new \finfo(FILEINFO_MIME_TYPE))->buffer($bytes);
            $this->verifyPdfBytes($bytes, is_string($mime) ? $mime : '');
            return;
        }
        $file = tempnam(storage_path('framework'), 'museum-check-');
        if ($file === false) throw new \RuntimeException('Cannot create private document inspection file');
        try {
            if (file_put_contents($file, $bytes, LOCK_EX) !== strlen($bytes)) {
                throw new \RuntimeException('Cannot write private document inspection file');
            }
            $this->verify($file, $extension);
        } finally {
            @unlink($file);
        }
    }

    /** One identical policy for disk-side PDF validation and fixed HTTP bytes. */
    private function verifyPdfBytes(string $pdf, string $mime): void
    {
        $header = substr($pdf, 0, 16);
        if (! str_starts_with($header, '%PDF-')
            || ! preg_match('/^%PDF-[12]\.[0-9]/', $header)
            || $mime !== 'application/pdf'
            || ! str_contains(substr($pdf, -2048), '%%EOF')
            || preg_match('#/(?:JavaScript|JS|Launch|RichMedia|EmbeddedFile|OpenAction)\b#i', $pdf)) {
            $this->invalid();
        }
    }

    private function invalid(): never
    {
        throw ValidationException::withMessages([
            'document' => 'Файл не прошёл проверку формата или безопасности. Для XLS требуется согласованная антивирусная обработка.',
        ]);
    }
}
