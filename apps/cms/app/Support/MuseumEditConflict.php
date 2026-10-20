<?php

declare(strict_types=1);

namespace App\Support;

use Symfony\Component\HttpKernel\Exception\HttpException;

/** Distinct from generic 409 responses: only this type may show editor drafts. */
final class MuseumEditConflict extends HttpException
{
    public function __construct(string $message)
    {
        parent::__construct(409, $message);
    }
}
