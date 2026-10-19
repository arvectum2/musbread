<?php

declare(strict_types=1);

namespace App\MoonShine\Fields;

use MoonShine\AssetManager\Css;
use MoonShine\AssetManager\Js;
use MoonShine\UI\Fields\Textarea;

/** MIT-licensed self-hosted editor, same HTML body and sanitizer pipeline. */
final class Jodit extends Textarea
{
    protected string $view = 'fields.jodit';

    protected function assets(): array
    {
        return [
            Css::make('vendor/museum-jodit/jodit.min.css'),
            Js::make('vendor/museum-jodit/jodit.min.js'),
            Js::make('vendor/museum-jodit/museum-jodit-init.js'),
        ];
    }
}
