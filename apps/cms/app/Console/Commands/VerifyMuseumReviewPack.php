<?php

declare(strict_types=1);

namespace App\Console\Commands;

use App\Support\MuseumReviewPackVerifier;
use Illuminate\Console\Command;

final class VerifyMuseumReviewPack extends Command
{
    protected $signature = 'museum:verify-review {file : Local JSON downloaded by a superuser} {--json : Return a machine-readable result}';
    protected $description = 'Read-only check that a full admin editorial review still matches current CMS and verified local release';

    public function handle(MuseumReviewPackVerifier $service): int
    {
        $result = $service->verify((string) $this->argument('file'));
        if ($this->option('json')) {
            $this->line(json_encode($result, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES | JSON_THROW_ON_ERROR));
        } elseif ($result['ok']) {
            $this->info($result['message']);
        } else {
            $this->error($result['message'].' ['.$result['code'].']');
        }
        return $result['ok'] ? self::SUCCESS : self::FAILURE;
    }
}
