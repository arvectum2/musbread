<?php

declare(strict_types=1);

namespace App\Support;

/** TZ-194. A mechanical wording policy, NOT automatic image recognition.
 * Actual correspondence between text and image requires the human editor. */
final class MuseumAltPolicy
{
    public const MAX_LENGTH = 125;

    public static function issue(?string $text): ?string
    {
        $value = trim(preg_replace('/\s+/u', ' ', (string) $text) ?? '');
        if ($value === '') return 'Добавьте содержательное описание видимого объекта.';
        if (mb_strlen($value) > self::MAX_LENGTH) {
            return 'Alt должен содержать не более 125 символов. Развёрнутую информацию внесите в отдельное поле.';
        }
        if (preg_match('/\b(?:картинк[а-яё]*|изображени[а-яё]*|фотографи[а-яё]*|фото|график[а-яё]*|picture|image|photo|graphic|graph)\b/iu', $value)) {
            return 'Не называйте тип файла («фото», «картинка», «изображение», «графика»); опишите то, что показано.';
        }
        if (preg_match('/[<>]/u', $value)) {
            return 'В описании недопустима HTML-разметка.';
        }
        return null;
    }
}
