<?php

declare(strict_types=1);

namespace App\Console\Commands;

use App\Support\MuseumPrivateBackup;
use Illuminate\Console\Command;

/** No public HTTP route. Operator with server access only. */
final class MuseumBackup extends Command
{
    protected $signature = 'museum:backup {--name= : Backup filename prefix (alphanumeric/underscore/dash only)}';
    protected $description = 'Create a private consistency-checked SQLite and uploaded-content backup';

    public function handle(MuseumPrivateBackup $backup): int
    {
        if (config('database.default') !== 'sqlite') {
            $this->error('Only SQLite backup supported; PostgreSQL requires pg_dump and separate policy.');
            return self::FAILURE;
        }
        $db = config('database.connections.sqlite.database');
        if (! is_string($db) || ! is_file($db)) { $this->error('Persistent SQLite database file required'); return self::FAILURE; }
        $prefix = $this->option('name') ?: 'museum-'.now()->format('Ymd-His');
        if (! preg_match('/^[a-zA-Z0-9][a-zA-Z0-9_-]{0,79}$/D', $prefix)) {
            $this->error('Unsafe archive basename'); return self::FAILURE;
        }
        $dir = storage_path('app/private/backups');
        if (! is_dir($dir)) mkdir($dir, 0700, true);
        chmod($dir, 0700);
        try {
            $file = $dir.'/'.$prefix.'.zip';
            $details = $backup->create($db, storage_path('app/private'), $file);
            $backup->verify($file);
            $this->info('Private backup saved: '.$file.' / '.$details['files'].' files / SHA-256 '.$details['sha256']);
            return self::SUCCESS;
        } catch (\Throwable $e) { $this->error($e->getMessage()); return self::FAILURE; }
    }
}
