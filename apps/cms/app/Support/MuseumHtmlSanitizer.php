<?php

namespace App\Support;

use HTMLPurifier;
use HTMLPurifier_Config;

final class MuseumHtmlSanitizer
{
    public function clean(string $html): string
    {
        $config = HTMLPurifier_Config::createDefault();
        $config->set('HTML.Allowed', 'p,br,strong,em,b,i,u,ul,ol,li,blockquote,h2,h3,h4,a[href|title],table,thead,tbody,tr,th,td');
        $config->set('URI.AllowedSchemes', ['http' => true, 'https' => true, 'mailto' => true]);
        $config->set('HTML.Nofollow', true);
        $config->set('Cache.SerializerPath', storage_path('framework/cache/data'));

        return (new HTMLPurifier($config))->purify($html);
    }
}
