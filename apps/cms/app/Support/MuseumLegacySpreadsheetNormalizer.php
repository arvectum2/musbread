<?php

namespace App\Support;

use Illuminate\Validation\ValidationException;
use Symfony\Component\Process\Process;

final class MuseumLegacySpreadsheetNormalizer
{
    /**
     * Produces a disposable, values-only XLSX. Original XLS bytes are never
     * retained. Explicitly disabled in production until museum AV/CDR approval.
     */
    public function normalize(string $source): string
    {
        if (app()->environment('production')) {
            throw ValidationException::withMessages([
                'document' => 'XLS недоступен до согласования антивирусной обработки с музеем.',
            ]);
        }
        $output = tempnam(sys_get_temp_dir(), 'musbread-normalized-');
        if ($output === false) {
            throw new \RuntimeException('Failed to create temporary normalization file.');
        }
        try {
            $process = new Process([
                'python3', base_path('../../scripts/normalize_xls.py'),
                '--input', $source, '--output', $output,
            ]);
            $process->setTimeout(9);
            $process->run();
            if (! $process->isSuccessful() || ! is_file($output)
                || filesize($output) > MuseumDocumentInspector::MAX_BYTES) {
                throw ValidationException::withMessages([
                    'document' => 'XLS не удалось безопасно преобразовать. Оригинал не сохранялся.',
                ]);
            }
            return $output;
        } catch (\Throwable $error) {
            @unlink($output);
            throw $error;
        }
    }
}
