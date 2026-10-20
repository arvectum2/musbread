<?php

declare(strict_types=1);

namespace App\Support;

use Illuminate\Support\Collection;

/** Fail closed before static media/documents are written.
 *
 * Video placeholders and reviewed accessible document editions MUST refer
 * to records that still have their exact approved rights and content.
 */
final class MuseumSnapshotPreflight
{
    public function validate(Collection $publicEntries): void
    {
        // Fail closed BEFORE exporting files if ANY CMS WYSIWYG placeholder
        // points at an unapproved, withdrawn or malformed publisher record.
        // This protects generated document/media directories from partial
        // changes caused by an invalid late-arriving video marker.
        foreach ($publicEntries as $publicEntry) {
            $body = (string) $publicEntry->body;
            preg_match_all('/\\[\\[museum-video:([a-z0-9]+(?:-[a-z0-9]+)*)\\]\\]/',
                $body, $tokens);
            // The public React renderer accepts only sanitized CMS HTML
            // paragraphs; reject tokens glued to other text or HTML.
            preg_match_all('~<p(?:\\s[^>]*)?>\\s*\\[\\[museum-video:([a-z0-9]+(?:-[a-z0-9]+)*)\\]\\]\\s*</p>~',
                $body, $placed);
            if (count($tokens[0]) !== substr_count($body, '[[museum-video:')
                || count($tokens[0]) !== count($placed[0])) {
                throw new \RuntimeException('Invalid inline placement for video marker in published entry: '.$publicEntry->slug);
            }
            $ready = $publicEntry->videos
                ->where('status', 'published')->keyBy('code');
            foreach ($tokens[1] as $code) {
                $candidate = $ready->get($code);
                if ($candidate === null
                    || MuseumVideoUrlPolicy::safeEmbed((string)$candidate->embed_url) !== $candidate->embed_url
                    || !MuseumVideoUrlPolicy::sourceValid((string)$candidate->source_url)
                    || !$candidate->rights_confirmed
                    || mb_strlen(trim((string)$candidate->transcript)) < 60) {
                    throw new \RuntimeException('Unapproved video marker in published entry: '.$publicEntry->slug);
                }
            }
        }

        // Accessible HTML is independent of the shorter accessibility note.
        // Never deliver an edition whose editorial approval no longer matches
        // the *current* PDF SHA and the *exact* cleaned text.
        $accessibleEdition = app(\App\Support\MuseumDocumentAccessibleEdition::class);
        foreach ($publicEntries as $publicEntry) {
            foreach ($publicEntry->documents as $document) {
                if ($document->accessible_edition_sha256 === null) continue;
                $html=(string)$document->accessible_html;
                if ($document->accessible_reviewed_at === null
                    || $document->accessible_reviewed_by === null
                    || $html === ''
                    || $accessibleEdition->clean($html) !== $html
                    || !hash_equals((string)$document->accessible_edition_sha256,
                        $accessibleEdition->signature((string)$document->sha256,$html))) {
                    throw new \RuntimeException('Accessible document edition needs new editorial approval: '.$document->id);
                }
                try {
                    $accessibleEdition->assertReviewable($html);
                } catch (\Illuminate\Validation\ValidationException $e) {
                    throw new \RuntimeException('Incomplete accessible HTML edition: '.$document->id,0,$e);
                }
            }
        }

    }
}
