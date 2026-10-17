<?php

declare(strict_types=1);

namespace App\Support;

use DOMDocument;
use DOMXPath;
use Illuminate\Support\Collection;

/** Check CMS detail-page hrefs against the next export, without HTTP requests. */
final class MuseumInternalLinkInspector
{
    private const ENTRY_PATHS = [
        'museum' => 'page', 'news' => 'news', 'excursions' => 'excursion',
        'exhibitions' => 'exhibition', 'documents' => 'document',
    ];

    /** @param Collection<string,bool> $availablePaths */
    public function __construct(private readonly Collection $availablePaths)
    {
    }

    /**
     * Only CMS detail routes and exported assets are checked. External links, anchors and other
     * static routes remain handled by the static-site nav audit.
     * @return list<array{level:string,code:string,message:string}>
     */
    public function check(string $html, string $sourcePath): array
    {
        if (trim($html) === '' || ! str_contains($html, '<')) return [];

        $dom = new DOMDocument();
        $previous = libxml_use_internal_errors(true);
        try {
            $dom->loadHTML('<?xml encoding="UTF-8"><html><body>'.$html.'</body></html>',
                LIBXML_NONET | LIBXML_NOERROR | LIBXML_NOWARNING);
            $nodes = (new DOMXPath($dom))->query('//a[@href]');
            if ($nodes === false) return [];
            $issues = [];
            $seen = [];
            foreach ($nodes as $node) {
                $href = trim($node->getAttribute('href'));
                if ($href === '' || str_starts_with($href, '#') || str_starts_with($href, '?')
                    || str_starts_with($href, '//')) continue;
                $parsed = parse_url($href);
                if ($parsed === false || isset($parsed['scheme']) || isset($parsed['host'])) continue;
                $path = $parsed['path'] ?? '';
                if ($path === '') continue;
                $path = rawurldecode($path);
                if (str_starts_with($path, '/')) {
                    $resolved = $path;
                } else {
                    $resolved = rtrim($sourcePath, '/').'/'.$path;
                }
                $parts = [];
                foreach (explode('/', $resolved) as $part) {
                    if ($part === '' || $part === '.') continue;
                    if ($part === '..') { array_pop($parts); continue; }
                    $parts[] = $part;
                }
                $segments = $parts;
                $english = ($segments[0] ?? '') === 'en';
                if ($english) array_shift($segments);
                $section = $segments[0] ?? '';
                $asset = $section === 'media' || ($section === 'documents'
                    && isset($segments[1]) && preg_match('/\.(?:pdf|docx|xlsx)$/iD', $segments[1]));
                if (! $asset && $section !== 'events' && ! isset(self::ENTRY_PATHS[$section])) continue;
                if (count($segments) === 1) continue; // Section index page, not a CMS detail.
                $normalized = '/'.implode('/', $parts).'/';
                if (isset($seen[$normalized])) continue;
                $seen[$normalized] = true;
                // A URL that resolves does NOT make "here"/an empty anchor
                // accessible or useful as editorial contextual linking.
                // External references and link text to non-CMS routes are
                // reviewed during author approval, not fabricated here.
                $anchorText=trim(preg_replace('/\\s+/u',' ',(string)$node->textContent) ?? '');
                if ($anchorText==='') {
                    $issues[]=[
                        'level'=>'error','code'=>'context_link_empty_text',
                        'message'=>'В тексте есть ссылка без видимого названия. Укажите смысловой текст ссылки.',
                    ];
                } elseif (preg_match('/^(?:здесь|тут|читать|читать далее|подробнее|ссылка|click here|read more)$/iuD',$anchorText)) {
                    $issues[]=[
                        'level'=>'warning','code'=>'context_link_generic_text',
                        'message'=>'Замените общее название ссылки смысловым названием материала или события.',
                    ];
                }
                if ($normalized===rtrim($sourcePath,'/').'/') {
                    $issues[]=[
                        'level'=>'warning','code'=>'context_link_to_same_page',
                        'message'=>'Ссылка ведёт на эту же страницу: проверьте, нужна ли она в тексте.',
                    ];
                }
                $validTarget = $asset
                    ? count($segments) === 2 && ! $english
                        && preg_match($section === 'media'
                            ? '/^[a-f0-9]{64}\.webp$/D'
                            : '/^[a-f0-9]{64}\.(?:pdf|docx|xlsx)$/D', $segments[1])
                    : count($segments) === 2
                        && preg_match('/^[a-z0-9]+(?:-[a-z0-9]+)*$/D', $segments[1]);
                if (! $validTarget) {
                    $issues[] = [
                        'level' => 'error', 'code' => 'internal_link_invalid',
                        'message' => 'В тексте есть некорректная внутренняя ссылка на материал, событие или файл.',
                    ];
                } elseif (! $this->availablePaths->has($normalized)) {
                    $issues[] = [
                        'level' => 'error', 'code' => $asset ? 'internal_asset_unavailable' : 'internal_link_unavailable',
                        'message' => $asset
                            ? 'В тексте есть ссылка на файл, отсутствующий в следующей выгрузке.'
                            : 'В тексте есть ссылка на материал или событие, отсутствующее в следующей выгрузке.',
                    ];
                }
            }
            return $issues;
        } finally {
            libxml_clear_errors();
            libxml_use_internal_errors($previous);
        }
    }

    /** @return array<string,string> */
    public static function entryPrefixes(): array
    {
        return self::ENTRY_PATHS;
    }
}
