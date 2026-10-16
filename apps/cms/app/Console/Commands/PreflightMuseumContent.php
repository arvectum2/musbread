<?php

declare(strict_types=1);

namespace App\Console\Commands;

use App\Support\MuseumContentPreflight;
use Illuminate\Console\Command;

final class PreflightMuseumContent extends Command
{
    protected $signature = 'museum:preflight {--strict : Exit with an error when public-ready entries have critical issues} {--json : Emit machine-readable JSON to terminal}';
    protected $description = 'Private, read-only editorial content check before publication';

    public function handle(MuseumContentPreflight $service): int
    {
        $report = $service->report();
        if ($this->option('json')) {
            $this->line(json_encode($report, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES | JSON_THROW_ON_ERROR));
        } else {
            $this->info("Материалов: {$report['total']}; готовы к экспорту: {$report['ready']}; критических ошибок в готовых: {$report['errors']}; предупреждений: {$report['warnings']}.");
            foreach ($report['records'] as $record) {
                if ($record['issues'] === []) continue;
                $this->line('#'.$record['id'].' ['.$record['state'].'] '.$record['slug']);
                foreach ($record['issues'] as $issue) {
                    $this->line('  '.strtoupper($issue['level']).' '.$issue['code'].': '.$issue['message']);
                }
            }
        }
        return $this->option('strict') && $report['errors'] > 0 ? self::FAILURE : self::SUCCESS;
    }
}
