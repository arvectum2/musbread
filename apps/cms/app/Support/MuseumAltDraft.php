<?php

declare(strict_types=1);

namespace App\Support;

use Illuminate\Validation\ValidationException;

/** TZ-188: a caption-based *draft*, not a claim of visual recognition.
 * An editor must confirm what is actually depicted before upload/publication.
 */
final class MuseumAltDraft
{
    public function suggest(string $caption): string
    {
        $candidate = trim(preg_replace('/\s+/u', ' ', strip_tags($caption)) ?? '');
        $candidate = preg_replace('/^(?:фото|фотография|иллюстрация|рисунок|photo)\s*[:№#-]\s*/iu', '', $candidate) ?? $candidate;
        $candidate = trim($candidate, " \n\r\t.!");
        $words = preg_split('/\s+/u', $candidate, -1, PREG_SPLIT_NO_EMPTY) ?: [];
        if (mb_strlen($candidate) < 12 || mb_strlen($candidate) > MuseumAltPolicy::MAX_LENGTH || count($words) < 3
            || preg_match('/^(?:изображение|фотография|картинка|image|photo)\s*(?:\d+)?$/iu', $candidate)
            || preg_match('/^(?:просто )?(?:(?:красивое|обычное|какое-то) )?(?:фото|фотография|изображение|картинка)$/iu', $candidate)
            || preg_match('/https?:\/\/|[<>]/iu', $candidate)) {
            throw ValidationException::withMessages([
                'caption' => 'Нужна содержательная подпись от 3 слов (12–125 символов), описывающая изображение. Автоматически распознать фотографию нельзя.',
            ]);
        }
        if ($issue = MuseumAltPolicy::issue($candidate)) {
            throw ValidationException::withMessages(['caption' => $issue]);
        }
        return mb_strtoupper(mb_substr($candidate, 0, 1)).mb_substr($candidate, 1);
    }
}
