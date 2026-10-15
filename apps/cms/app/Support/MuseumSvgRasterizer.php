<?php

namespace App\Support;

use DOMDocument;
use DOMElement;
use DOMNode;
use Illuminate\Validation\ValidationException;
use Symfony\Component\Process\Process;

/**
 * Very restrictive *static geometry only* SVG subset. It rejects references,
 * CSS, scripts, animation, embedded images, SVG filters, doctypes and entities.
 * No original SVG bytes are served from the public site.
 */
final class MuseumSvgRasterizer
{
    private const ELEMENTS = [
        'svg', 'g', 'path', 'rect', 'circle', 'ellipse', 'line',
        'polyline', 'polygon', 'title', 'desc',
    ];
    private const ATTRIBUTES = [
        'xmlns', 'viewBox', 'width', 'height', 'x', 'y', 'x1', 'y1', 'x2', 'y2',
        'cx', 'cy', 'r', 'rx', 'ry', 'points', 'd', 'fill', 'stroke',
        'stroke-width', 'opacity', 'fill-opacity', 'stroke-opacity',
        'stroke-linecap', 'stroke-linejoin', 'fill-rule',
    ];

    /** @return array{0:string,1:int,2:int} A clean PNG and dimensions */
    public function render(string $raw): array
    {
        if (strlen($raw) < 30 || strlen($raw) > 100 * 1024
            || preg_match('/<!|<\?|&(?:#|[a-z])/i', $raw)) {
            $this->invalid();
        }
        $document = new DOMDocument();
        $previous = libxml_use_internal_errors(true);
        try {
            $valid = $document->loadXML($raw, LIBXML_NONET | LIBXML_NOERROR | LIBXML_NOWARNING);
        } finally {
            libxml_clear_errors();
            libxml_use_internal_errors($previous);
        }
        if (! $valid || $document->doctype !== null || ! $document->documentElement
            || $document->documentElement->localName !== 'svg'
            || $document->documentElement->namespaceURI !== 'http://www.w3.org/2000/svg') {
            $this->invalid();
        }
        $root = $document->documentElement;
        $width = $root->getAttribute('width');
        $height = $root->getAttribute('height');
        if (! preg_match('/^[1-9][0-9]{0,3}$/D', $width)
            || ! preg_match('/^[1-9][0-9]{0,3}$/D', $height)
            || (int) $width > 2048 || (int) $height > 2048
            || (int) $width * (int) $height > 4_000_000) {
            $this->invalid();
        }
        $count = 0;
        $this->validateNode($root, 0, $count);
        $command = ['rsvg-convert', '-f', 'png', '-w', $width, '-h', $height, '-'];
        $process = new Process($command);
        $process->setInput($raw);
        $process->setTimeout(4);
        try {
            $process->run();
        } catch (\Throwable $error) {
            $this->invalid();
        }
        $png = $process->getOutput();
        if (! $process->isSuccessful() || strlen($png) > 5 * 1024 * 1024
            || (@getimagesizefromstring($png)[2] ?? null) !== IMAGETYPE_PNG) {
            $this->invalid();
        }
        return [$png, (int) $width, (int) $height];
    }

    private function validateNode(DOMNode $node, int $depth, int &$count): void
    {
        if ($depth > 18 || ++$count > 700) $this->invalid();
        if ($node instanceof DOMElement) {
            if (! in_array($node->localName, self::ELEMENTS, true)
                || $node->namespaceURI !== 'http://www.w3.org/2000/svg') $this->invalid();
            foreach ($node->attributes as $attribute) {
                $name = $attribute->nodeName;
                $value = $attribute->value;
                if (! in_array($name, self::ATTRIBUTES, true) || strlen($value) > 2500
                    || preg_match('/url\s*\(|(?:javascript|data|file|http|https):|@import|<|>|&/i', $value)) {
                    $this->invalid();
                }
                if ($name === 'xmlns' && $value !== 'http://www.w3.org/2000/svg') $this->invalid();
                if (in_array($name, ['fill','stroke'], true)
                    && ! preg_match('/^(?:none|transparent|#[0-9a-fA-F]{3,8}|[a-zA-Z]{1,24})$/D', $value)) {
                    $this->invalid();
                }
            }
        } elseif ($node->nodeType !== XML_TEXT_NODE || trim($node->textContent) !== ''
            && ! in_array($node->parentNode?->localName, ['title', 'desc'], true)) {
            $this->invalid();
        }
        foreach ($node->childNodes as $child) {
            $this->validateNode($child, $depth + 1, $count);
        }
    }

    private function invalid(): never
    {
        throw ValidationException::withMessages([
            'image' => 'SVG не прошёл проверку безопасной геометрии и возможности преобразования.',
        ]);
    }
}
