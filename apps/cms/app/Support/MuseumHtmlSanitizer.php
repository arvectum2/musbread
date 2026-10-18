<?php

namespace App\Support;

use HTMLPurifier;
use HTMLPurifier_Config;

final class MuseumHtmlSanitizer
{
    public function clean(string $html): string
    {
        $config = HTMLPurifier_Config::createDefault();
        // Keep accessible official-document table relationships without
        // allowing embedded objects, arbitrary scripts, styles or iframes.
        $config->set('HTML.DefinitionID', 'MuseumSafeAccessibleTables');
        $config->set('HTML.DefinitionRev', 1);
        // HTMLPurifier Tables module omits standard aria-free HTML
        // td[headers] associations. Add as text-only token references; all
        // HTML is sanitized and HTML tables remain fully inert.
        $config->set('HTML.Allowed', 'p,br,strong,em,b,i,u,ul,ol,li,blockquote,h2,h3,h4,a[href|title],table,caption,thead,tbody,tfoot,tr,th[scope|id|colspan|rowspan],td[headers|colspan|rowspan]');
        $config->set('URI.AllowedSchemes', ['http' => true, 'https' => true, 'mailto' => true]);
        $config->set('HTML.Nofollow', true);
        $config->set('Cache.SerializerPath', storage_path('framework/cache/data'));

        if ($definition = $config->maybeGetRawHTMLDefinition()) {
            $definition->addAttribute('td', 'headers', 'Text');
        }


        return (new HTMLPurifier($config))->purify($html);
    }
}
