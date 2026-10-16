<?php

declare(strict_types=1);

namespace App\Support;

use Illuminate\Validation\ValidationException;
use Symfony\Component\Process\Process;

/** TZ-182. Parse structural GIF blocks before handing bounded animation to libwebp.
 * Never expose the original GIF or source metadata to the public static release.
 */
final class MuseumGifProcessor
{
    /** @return array{0:int,1:int} Number of frames and total centiseconds. */
    public function inspect(string $raw, int $width, int $height): array
    {
        $length = strlen($raw);
        // Static GIF stays within the existing general upload bounds; stricter
        // animation limits apply only after a real second frame is detected.
        if ($length < 20 || $length > 5_242_880 || $width > 4096 || $height > 4096
            || $width * $height > 16_000_000 || ! in_array(substr($raw, 0, 6), ['GIF87a', 'GIF89a'], true)) $this->invalid();
        $at = 13;
        if ((ord($raw[10]) & 0x80) !== 0) $at += 3 * (1 << ((ord($raw[10]) & 7) + 1));
        if ($at >= $length) $this->invalid();
        $frames = 0;
        $duration = 0;
        $pendingDelay = 0;
        $trailer = false;
        while ($at < $length) {
            $marker = ord($raw[$at++]);
            if ($marker === 0x3b) { $trailer = $at === $length; break; }
            if ($marker === 0x21) {
                if ($at >= $length) $this->invalid();
                $label = ord($raw[$at++]);
                if ($label === 0xf9) {
                    if ($at + 6 > $length || ord($raw[$at]) !== 4 || ord($raw[$at + 5]) !== 0) $this->invalid();
                    $pendingDelay = unpack('v', substr($raw, $at + 2, 2))[1];
                    $at += 6;
                } else {
                    $this->skipBlocks($raw, $length, $at);
                }
            } elseif ($marker === 0x2c) {
                if ($at + 10 > $length) $this->invalid();
                $frameW = unpack('v', substr($raw, $at + 4, 2))[1];
                $frameH = unpack('v', substr($raw, $at + 6, 2))[1];
                if ($frameW < 1 || $frameH < 1 || $frameW > $width || $frameH > $height) $this->invalid();
                $flags = ord($raw[$at + 8]);
                $at += 9;
                if (($flags & 0x80) !== 0) $at += 3 * (1 << (($flags & 7) + 1));
                if ($at >= $length || ord($raw[$at++]) > 8) $this->invalid();
                $this->skipBlocks($raw, $length, $at);
                if (++$frames > 60) $this->invalid();
                $duration += max(2, $pendingDelay);
                if ($duration > 3000) $this->invalid();
                $pendingDelay = 0;
            } else $this->invalid();
        }
        if (! $trailer || $frames < 1) $this->invalid();
        if ($frames > 1 && ($length > 2_097_152 || $width > 1024 || $height > 1024
            || $width * $height > 1_048_576)) $this->invalid();
        return [$frames, $duration];
    }

    private function skipBlocks(string $bytes, int $length, int &$pos): void
    {
        while (true) {
            if ($pos >= $length) $this->invalid();
            $size = ord($bytes[$pos++]);
            if ($size === 0) return;
            if ($pos + $size > $length) $this->invalid();
            $pos += $size;
        }
    }

    public function convertAnimation(string $gif, int $width, int $height): string
    {
        $staging = storage_path('app/private');
        if (is_link($staging) || (! is_dir($staging) && ! mkdir($staging, 0700, true))) $this->invalid();
        if (! is_writable($staging)) $this->invalid();
        $input = tempnam($staging, '.gif-staged-');
        $output = tempnam($staging, '.webp-staged-');
        if ($input === false || $output === false) {
            if ($input) @unlink($input);
            if ($output) @unlink($output);
            $this->invalid();
        }
        chmod($input, 0600); chmod($output, 0600);
        try {
            if (file_put_contents($input, $gif) !== strlen($gif)) $this->invalid();
            // gif2webp from libwebp: re-encodes decoded frames (no source metadata).
            // This is an optional explicit server dependency, never run via a shell.
            $process = new Process(['gif2webp', '-quiet', '-lossy', '-q', '78', '-m', '3',
                '-metadata', 'none', $input, '-o', $output]);
            $process->setTimeout(9);
            try { $process->run(); } catch (\Throwable) { $this->invalid(); }
            if (! $process->isSuccessful() || ! is_file($output)
                || filesize($output) > 5_242_880) $this->invalid();
            $clean = file_get_contents($output);
            if (! is_string($clean) || ! str_starts_with($clean, 'RIFF')
                || substr($clean, 8, 4) !== 'WEBP'
                || ! str_contains($clean, 'ANIM') || ! str_contains($clean, 'ANMF')
                || (@getimagesizefromstring($clean)[2] ?? null) !== IMAGETYPE_WEBP) $this->invalid();
            $image = getimagesizefromstring($clean);
            if ($image[0] !== $width || $image[1] !== $height) $this->invalid();
            return $clean;
        } finally {
            @unlink($input);
            @unlink($output);
        }
    }

    private function invalid(): never
    {
        throw ValidationException::withMessages([
            'image' => 'GIF не прошёл безопасную проверку кадров или преобразование в WebP (требуется gif2webp).',
        ]);
    }
}
