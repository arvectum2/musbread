<?php

namespace Tests\Feature;

use App\Jobs\PublishMuseumSnapshot;
use App\Models\MuseumEntry;
use App\Models\MuseumPublicationRun;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Tests\TestCase;

class MuseumQueuedPrivateStageTest extends TestCase
{
    use RefreshDatabase;

    public function test_real_worker_exports_content_only_to_private_staging_without_touching_fixture(): void
    {
        $stage = storage_path('framework/testing/private-stage-'.bin2hex(random_bytes(5)));
        mkdir($stage, 0700, true);
        config(['museum.queued_export_staging_dir' => $stage]);
        MuseumEntry::create([
            'type' => 'news', 'slug' => 'actual-queue-stage-news',
            'title' => 'QA: Проверенная новость из очереди',
            'body' => '<p>Только опубликованные данные без частных записей.</p>',
            'status' => 'published',
        ]);
        MuseumEntry::create([
            'type' => 'news', 'slug' => 'private-queue-draft',
            'title' => 'НЕ ПОКАЗЫВАТЬ ЧЕРНОВИК',
            'body' => 'Черновик редактора',
            'status' => 'draft',
        ]);
        $run = MuseumPublicationRun::create(['status' => 'queued']);
        $fixture = base_path('../web/src/data/published.json');
        $before = hash_file('sha256', $fixture);
        try {
            (new PublishMuseumSnapshot($run->id))->handle();
            $run->refresh();
            $this->assertSame('succeeded', $run->status);
            $this->assertSame(1, $run->attempts);
            $this->assertSame($before, hash_file('sha256', $fixture));
            $snapshot = $stage.'/published.json';
            $manifest = $stage.'/snapshot-manifest.json';
            $this->assertFileExists($snapshot);
            $this->assertFileExists($manifest);
            $data = json_decode(file_get_contents($snapshot), true, flags: JSON_THROW_ON_ERROR);
            $slugs = array_column($data['entries'], 'slug');
            $this->assertContains('actual-queue-stage-news', $slugs);
            $this->assertNotContains('private-queue-draft', $slugs);
            $verified = json_decode(file_get_contents($manifest), true, flags: JSON_THROW_ON_ERROR);
            $this->assertSame(hash_file('sha256', $snapshot), $verified['files']['published.json']['sha256']);
            $this->assertSame(hash_file('sha256', $snapshot), $run->snapshot_sha256);
            (new PublishMuseumSnapshot($run->id))->handle();
            $this->assertSame(1, $run->fresh()->attempts);
        } finally {
            foreach (glob($stage.'/*') ?: [] as $file) {
                if (is_file($file)) unlink($file);
                if (is_dir($file)) rmdir($file);
            }
            rmdir($stage);
        }
    }

    public function test_queued_staging_refuses_real_public_webroot_even_if_existing(): void
    {
        config(['museum.queued_export_staging_dir' => base_path('../web/public')]);
        $run = MuseumPublicationRun::create(['status' => 'queued']);
        try {
            (new PublishMuseumSnapshot($run->id))->handle();
            $this->fail('Existing public webroot accepted as supposedly private queue staging');
        } catch (\RuntimeException $exception) {
            $this->assertStringContainsString('cannot be inside public', $exception->getMessage());
            $this->assertSame('failed', $run->fresh()->status);
            $this->assertNull($run->fresh()->snapshot_sha256);
        }
    }

    public function test_invalid_private_staging_directory_blocks_export_and_records_failure(): void
    {
        config(['museum.queued_export_staging_dir' => storage_path('framework/testing/missing-stage-'.bin2hex(random_bytes(6)))]);
        $run = MuseumPublicationRun::create(['status' => 'queued']);
        try {
            (new PublishMuseumSnapshot($run->id))->handle();
            $this->fail('Queue unexpectedly published with a nonexistent private stage');
        } catch (\RuntimeException $exception) {
            $this->assertStringContainsString('Unsafe private queued export staging', $exception->getMessage());
            $this->assertSame('failed', $run->fresh()->status);
            $this->assertNull($run->fresh()->snapshot_sha256);
            $this->assertSame(1, $run->fresh()->attempts);
        }
    }
}
