<?php

declare(strict_types=1);

// CLI-only multi-process test adapter. Never opens production DB.
// Usage: php qa_shared_museum_entry_worker.php init|save|read ...
// DB_DATABASE must be an existing throwaway .local_archive/sqlite-race-* file.

use App\Models\MuseumEntry;
use App\Support\MuseumApprovalRevision;
use App\Support\MuseumEntryRevisionGuard;
use Illuminate\Contracts\Console\Kernel;
use Illuminate\Support\Facades\DB;

$root = dirname(__DIR__);
$archive = realpath($root.'/.local_archive');
$db = getenv('DB_DATABASE');
if ($archive === false || ! is_string($db) || ! is_file($db)
    || dirname(realpath($db) ?: '') !== $archive
    || ! preg_match('/^sqlite-race-[a-f0-9]{24}\.sqlite$/D', basename($db))
    || getenv('DB_CONNECTION') !== 'sqlite' || getenv('DB_URL') !== '') {
    fwrite(STDERR, "Unsafe test database; refusing to connect\n");
    exit(3);
}
require $root.'/apps/cms/vendor/autoload.php';
$app = require $root.'/apps/cms/bootstrap/app.php';
$app->make(Kernel::class)->bootstrap();

$action = $argv[1] ?? '';
if ($action === 'init') {
    $entry = MuseumEntry::create([
        'type' => 'news', 'slug' => 'shared-sqlite-race-fixture',
        'title' => 'Изолированный тест редактирования',
        'body' => '<p>Первоначальная редакция</p>',
        'status' => 'draft',
    ]);
    echo json_encode(['id' => $entry->id,
        'revision' => MuseumApprovalRevision::fingerprint($entry)], JSON_THROW_ON_ERROR), "\n";
    exit(0);
}
if ($action === 'read') {
    $entry = MuseumEntry::query()->findOrFail((int) ($argv[2] ?? 0));
    echo json_encode(['body' => $entry->body,
        'revision' => MuseumApprovalRevision::fingerprint($entry)], JSON_THROW_ON_ERROR), "\n";
    exit(0);
}
if ($action !== 'save') exit(4);

[$script, $verb, $entryId, $revision, $actor, $ready, $go] = $argv;
$check = static function (string $path, string $prefix) use ($archive): bool {
    return dirname($path) === $archive
        && preg_match('/^'.preg_quote($prefix, '/').'[a-f0-9]{24}$/D', basename($path));
};
if (! $check($ready, 'shared-ready-') || ! $check($go, 'shared-go-')
    || ! preg_match('/^[AB]$/D', $actor)) {
    fwrite(STDERR, "Invalid test process barrier\n");
    exit(4);
}

try {
    // Release both workers together BEFORE they acquire the write fence.
    // Once CAS reserves the edit_version, the other transaction must wait
    // (or fail closed on SQLite), never block our process barrier.
    file_put_contents($ready, "READY\n");
    $deadline = microtime(true) + 15;
    while (! file_exists($go) && microtime(true) < $deadline) {
        usleep(10000);
    }
    if (! file_exists($go)) throw new RuntimeException('Timed out waiting for test barrier');
    DB::transaction(function () use ($entryId, $revision, $actor) {
        $fresh = app(MuseumEntryRevisionGuard::class)->assertCurrent((int) $entryId, $revision);
        $fresh->body = '<p>Редактор '.$actor.' сохранил обновление</p>';
        $fresh->save();
    }, 3);
    echo "COMMITTED ".$actor."\n";
    exit(0);
} catch (Throwable $e) {
    // In SQLite a concurrent deferred read->write may fail with SQLITE_BUSY,
    // rather than waiting for a row lock as PostgreSQL/MySQL would.
    $class = class_basename($e);
    if ($e instanceof \Symfony\Component\HttpKernel\Exception\HttpException
        && $e->getStatusCode() === 409) {
        echo "CONFLICT_409 ".$actor."\n";
        exit(9);
    }
    if ($e instanceof \Illuminate\Database\QueryException
        && str_contains(strtolower($e->getMessage()), 'locked')) {
        echo "CONFLICT_SQLITE_BUSY ".$actor."\n";
        exit(9);
    }
    fwrite(STDERR, $class.': '.$e->getMessage()."\n");
    exit(6);
}
