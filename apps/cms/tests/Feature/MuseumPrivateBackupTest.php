<?php

declare(strict_types=1);

namespace Tests\Feature;

use App\Support\MuseumPrivateBackup;
use SQLite3;
use Tests\TestCase;
use ZipArchive;

final class MuseumPrivateBackupTest extends TestCase
{
    private string $tmp;

    protected function setUp(): void
    {
        parent::setUp();
        $this->tmp = sys_get_temp_dir().'/museum-backup-test-'.bin2hex(random_bytes(6));
        mkdir($this->tmp, 0700);
    }

    protected function tearDown(): void
    {
        $it = new \RecursiveIteratorIterator(new \RecursiveDirectoryIterator($this->tmp, \FilesystemIterator::SKIP_DOTS), \RecursiveIteratorIterator::CHILD_FIRST);
        foreach ($it as $file) $file->isDir() && ! $file->isLink() ? rmdir($file->getPathname()) : unlink($file->getPathname());
        rmdir($this->tmp);
        parent::tearDown();
    }

    public function test_roundtrip_with_sqlite_and_private_files_keeps_live_original_unchanged(): void
    {
        $db = $this->tmp.'/source.sqlite';
        $conn = new SQLite3($db);
        $conn->exec('CREATE TABLE inventory (id INTEGER PRIMARY KEY, label TEXT)');
        $conn->exec("INSERT INTO inventory (label) VALUES ('Private example')");
        $conn->close();
        mkdir($this->tmp.'/private', 0700);
        mkdir($this->tmp.'/private/media', 0700);
        file_put_contents($this->tmp.'/private/media/photo.webp', 'PRIVATE-IMAGE-BYTES');
        mkdir($this->tmp.'/private/backups',0700);
        file_put_contents($this->tmp.'/private/backups/old.zip','never-nest-backups');
        $svc = new MuseumPrivateBackup();
        $archive = $this->tmp.'/private/backups/fixture.zip';
        $result = $svc->create($db,$this->tmp.'/private',$archive);
        $this->assertSame(2,$result['files']);
        $this->assertSame(hash_file('sha256',$archive),$result['sha256']);
        $this->assertSame(2,$svc->verify($archive)['files']);
        $this->assertSame(0600, fileperms($archive) & 0777);
        $this->assertSame(false, strpos(file_get_contents($archive),'never-nest-backups'));
        $restore=$this->tmp.'/restored';
        $svc->restoreToNewDirectory($archive,$restore);
        $this->assertSame('PRIVATE-IMAGE-BYTES', file_get_contents($restore.'/private/media/photo.webp'));
        $restoredDb = new SQLite3($restore.'/database.sqlite', SQLITE3_OPEN_READONLY);
        $this->assertSame('Private example',$restoredDb->querySingle('SELECT label FROM inventory'));
        $restoredDb->close();
        $this->assertSame(0700, fileperms($restore) & 0777);
        $this->assertSame(0600, fileperms($restore.'/database.sqlite') & 0777);
        $original=new SQLite3($db);
        $this->assertSame(1,$original->querySingle('SELECT COUNT(*) FROM inventory'));
        $original->close();
        $this->expectException(\RuntimeException::class);
        $svc->restoreToNewDirectory($archive,$restore);
    }

    public function test_tampered_zip_content_is_rejected_before_any_restore(): void
    {
        $db = $this->tmp.'/source.sqlite';
        $sqlite = new SQLite3($db);$sqlite->exec('CREATE TABLE data (n INTEGER)');$sqlite->close();
        $svc=new MuseumPrivateBackup();
        $zip=$this->tmp.'/valid.zip';$svc->create($db,$this->tmp.'/none',$zip);
        $z=new ZipArchive();$z->open($zip);$z->addFromString('database.sqlite','tampered');$z->close();
        $this->expectException(\RuntimeException::class);
        $svc->restoreToNewDirectory($zip,$this->tmp.'/should-not-exist');
    }

    public function test_zip_slip_and_unexpected_entries_fail_closed(): void
    {
        $db=$this->tmp.'/source.sqlite';$sqlite=new SQLite3($db);$sqlite->exec('CREATE TABLE data (n INTEGER)');$sqlite->close();
        $svc=new MuseumPrivateBackup();$zip=$this->tmp.'/valid.zip';$svc->create($db,$this->tmp.'/none',$zip);
        $z=new ZipArchive();$z->open($zip);$z->addFromString('../evil','leak');$z->close();
        $this->expectException(\RuntimeException::class);$svc->verify($zip);
    }

    public function test_refuses_backup_overwrite(): void
    {
        $db=$this->tmp.'/source.sqlite';$sqlite=new SQLite3($db);$sqlite->exec('CREATE TABLE data (n INTEGER)');$sqlite->close();
        $svc=new MuseumPrivateBackup();$zip=$this->tmp.'/valid.zip';$svc->create($db,$this->tmp.'/none',$zip);
        $this->expectException(\RuntimeException::class);$svc->create($db,$this->tmp.'/none',$zip);
    }
}
