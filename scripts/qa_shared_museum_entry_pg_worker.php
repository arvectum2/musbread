<?php
declare(strict_types=1);

// This test adapter is ALLOWED to connect only to an isolated DB named
// musbread_qa_* at 127.0.0.1, with a unique test-only username.
// Never open any production database from this script.
use App\Models\MuseumEntry;
use App\Support\MuseumApprovalRevision;
use App\Support\MuseumEntryRevisionGuard;
use Illuminate\Contracts\Console\Kernel;
use Illuminate\Support\Facades\DB;

if (getenv('DB_CONNECTION') !== 'pgsql'
    || getenv('DB_HOST') !== '127.0.0.1'
    || ! preg_match('/^musbread_qa_[a-f0-9]{12}$/D', (string)getenv('DB_DATABASE'))
    || ! preg_match('/^musbread_qa_[a-f0-9]{12}$/D', (string)getenv('DB_USERNAME'))
    || getenv('MUSBREAD_QA_EXPLICIT') !== '1'
    || ! preg_match('/^[0-9]{2,5}$/D', (string)getenv('DB_PORT'))
    || getenv('DB_URL') !== '') {
    fwrite(STDERR, "Refused unsafe PostgreSQL QA environment\n");
    exit(3);
}
require dirname(__DIR__).'/apps/cms/vendor/autoload.php';
$app = require dirname(__DIR__).'/apps/cms/bootstrap/app.php';
$app->make(Kernel::class)->bootstrap();
$action = $argv[1] ?? '';
if ($action === 'init') {
    $entry = MuseumEntry::create([
        'type'=>'news', 'slug'=>'pg-test-shared-entry',
        'title'=>'Synthetic test', 'body'=>'<p>Baseline</p>', 'status'=>'draft',
    ]);
    echo json_encode(['id'=>$entry->id,'revision'=>MuseumApprovalRevision::fingerprint($entry)], JSON_THROW_ON_ERROR),"\n";
    exit(0);
}
if ($action === 'read') {
    $entry = MuseumEntry::query()->findOrFail((int)($argv[2]??0));
    echo json_encode(['body'=>$entry->body,'revision'=>MuseumApprovalRevision::fingerprint($entry)], JSON_THROW_ON_ERROR),"\n";
    exit(0);
}
if ($action !== 'save') exit(4);
[$script,$action,$id,$revision,$actor,$ready,$go] = $argv;
$archive = realpath(dirname(__DIR__).'/.local_archive');
$safe = static function(string $file,string $prefix) use($archive):bool {
    return dirname($file) === $archive &&
        preg_match('/^'.preg_quote($prefix,'/').'[a-f0-9]{24}$/D',basename($file))===1;
};
if (!$safe($ready,'pg-ready-') || !$safe($go,'pg-go-') ||
    ! preg_match('/^[AB]$/D',$actor)) exit(4);
try {
    file_put_contents($ready,"READY\n");
    $deadline = microtime(true)+15;
    while (!file_exists($go) && microtime(true)<$deadline)usleep(10000);
    if (!file_exists($go))throw new RuntimeException('Barrier deadline');
    DB::transaction(static function()use($id,$revision,$actor):void{
        $fresh=app(MuseumEntryRevisionGuard::class)->assertCurrent((int)$id,$revision);
        $fresh->body='<p>Editor '.$actor.' saved</p>';
        $fresh->save();
    },3);
    echo "COMMITTED ".$actor."\n";
    exit(0);
} catch (Throwable $e) {
    if ($e instanceof \Symfony\Component\HttpKernel\Exception\HttpException
        && $e->getStatusCode()===409) {
        echo "CONFLICT_409 ".$actor."\n";
        exit(9);
    }
    fwrite(STDERR,get_class($e).': '.$e->getMessage()."\n");
    exit(6);
}
