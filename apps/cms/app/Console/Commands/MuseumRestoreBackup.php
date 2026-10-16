<?php

declare(strict_types=1);

namespace App\Console\Commands;

use App\Support\MuseumPrivateBackup;
use Illuminate\Console\Command;

final class MuseumRestoreBackup extends Command
{
    protected $signature = 'museum:restore-backup {name : Existing backup basename} {--verify-only : Check content hashes without writing any files}';
    protected $description = 'Verify or restore to an isolated private folder (never overwrite live CMS)';

    public function handle(MuseumPrivateBackup $backup): int
    {
        $name = (string)$this->argument('name');
        if (! preg_match('/^[a-zA-Z0-9][a-zA-Z0-9_-]{0,79}$/D', $name)) {
            $this->error('Unsafe archive basename'); return self::FAILURE;
        }
        $dir = storage_path('app/private');
        $file = $dir.'/backups/'.$name.'.zip';
        try {
            if ($this->option('verify-only')) {
                $report = $backup->verify($file);
                $this->info('Verified: '.$report['files'].' files');
            } else {
                $target = $dir.'/restores';
                if (! is_dir($target)) mkdir($target, 0700, true);
                chmod($target, 0700);
                $report = $backup->restoreToNewDirectory($file, $target.'/'.$name);
                $this->warn('Restored for inspection ONLY to '.$target.'/'.$name.' ('.$report['files'].' files). Live CMS was NOT changed.');
            }
            return self::SUCCESS;
        } catch (\Throwable $e) { $this->error($e->getMessage()); return self::FAILURE; }
    }
}
