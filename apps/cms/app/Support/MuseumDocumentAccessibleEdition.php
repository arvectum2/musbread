<?php

namespace App\Support;

use Illuminate\Validation\ValidationException;

/** An editorial full-text HTML *candidate*, not OCR and not PDF/UA proof.
 * The reviewer alone certifies equivalence, bound to an immutable source SHA.
 */
final class MuseumDocumentAccessibleEdition
{
    public const MAX_BYTES = 200000;

    public function clean(string $source): string
    {
        if (strlen($source)>self::MAX_BYTES) {
            throw ValidationException::withMessages([
                'accessible_html'=>'HTML-редакция превышает 200 КБ; разделите документ.',
            ]);
        }
        return app(MuseumHtmlSanitizer::class)->clean($source);
    }

    public function assertReviewable(string $html): void
    {
        $text=trim(preg_replace('/\s+/u',' ',html_entity_decode(strip_tags($html),
            ENT_QUOTES | ENT_HTML5,'UTF-8')) ?? '');
        if(mb_strlen($text)<300
            || !preg_match('/<(?:p|h2|h3|h4|li|td)\b/i',$html)) {
            throw ValidationException::withMessages([
                'accessible_html'=>'Для публикации нужна содержательная проверенная полная HTML-версия (не менее 300 символов текста), а не аннотация PDF.',
            ]);
        }
    }

    public function signature(string $sourceSha, string $html): string
    {
        if(!preg_match('/^[a-f0-9]{64}$/D',$sourceSha)) {
            throw ValidationException::withMessages([
                'source_sha256'=>'Неверная контрольная сумма оригинала.',
            ]);
        }
        return hash('sha256',"museum-accessible-edition-v1\n".$sourceSha."\n".$html);
    }
}
