<?php

namespace Tests\Feature;

use App\Models\MuseumEntry;
use App\Models\MuseumSection;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Cache;
use MoonShine\Laravel\Models\MoonshineUser;
use MoonShine\Laravel\Models\MoonshineUserRole;
use Tests\TestCase;

final class MuseumBackendSecurityCacheTest extends TestCase
{
    use RefreshDatabase;

    public function test_cache_probe_supports_real_database_store_and_publication_lock_survives(): void
    {
        $previous = config('cache.default');
        try {
            config(['cache.default' => 'database']);
            Cache::purge('database');
            $this->artisan('museum:cache-check', ['--require-shared'=>true])
                ->expectsOutputToContain('CACHE OK')->assertSuccessful();
            $this->assertDatabaseCount('cache', 0);
            $this->assertDatabaseCount('cache_locks', 0);

            // The probe uses unique ephemeral keys: it MUST NOT unlock
            // the existing publication lock or mutate publication records.
            $publicationLock = Cache::lock('museum:publication-export', 20);
            $this->assertTrue($publicationLock->get());
            try {
                $this->artisan('museum:cache-check', ['--require-shared'=>true])
                    ->assertSuccessful();
                $rival = Cache::lock('museum:publication-export', 20);
                $this->assertFalse($rival->get());
            } finally {
                $publicationLock->release();
            }
            $this->assertDatabaseCount('cache_locks', 0);
        } finally {
            config(['cache.default'=>$previous]);
            Cache::purge('database');
        }
    }

    public function test_multi_worker_check_rejects_process_local_array_cache_without_side_effects(): void
    {
        $this->artisan('museum:cache-check', ['--require-shared'=>true])
            ->expectsOutputToContain('not an approved multi-worker')
            ->assertFailed();
        $this->artisan('museum:cache-check')->assertSuccessful();
        $this->assertDatabaseCount('museum_publication_runs', 0);
    }

    public function test_systemd_preflight_requires_explicit_queue_and_safe_retry_window(): void
    {
        $old = [
            'cache.default'=>config('cache.default'),
            'museum.queue_publication'=>config('museum.queue_publication'),
            'queue.default'=>config('queue.default'),
            'queue.connections.database.retry_after'=>config('queue.connections.database.retry_after'),
        ];
        try {
            config(['cache.default'=>'database', 'queue.default'=>'database',
                'queue.connections.database.retry_after'=>900,
                'museum.queue_publication'=>false]);
            Cache::purge('database');
            $this->artisan('museum:cache-check', ['--require-queue-worker'=>true])
                ->expectsOutputToContain('not safely configured')->assertFailed();

            config(['museum.queue_publication'=>true]);
            $this->artisan('museum:cache-check', ['--require-queue-worker'=>true])
                ->expectsOutputToContain('CACHE OK')->assertSuccessful();

            config(['queue.connections.database.retry_after'=>600]);
            $this->artisan('museum:cache-check', ['--require-queue-worker'=>true])
                ->assertFailed();
            config(['queue.connections.database.retry_after'=>900,'queue.default'=>'sync']);
            $this->artisan('museum:cache-check', ['--require-queue-worker'=>true])
                ->assertFailed();
            $this->assertDatabaseCount('cache', 0);
            $this->assertDatabaseCount('cache_locks', 0);
            $this->assertDatabaseCount('museum_publication_runs', 0);
        } finally {
            config($old);
            Cache::purge('database');
        }
    }

    public function test_orm_filter_resists_forged_section_ids_and_sql_like_search_queries(): void
    {
        $my = MuseumSection::create(['slug'=>'my-sec','title'=>'Мои материалы','status'=>'published']);
        $foreign = MuseumSection::create(['slug'=>'secret-sec','title'=>'Закрытые материалы','status'=>'published']);
        MuseumEntry::create(['type'=>'news','title'=>'Разрешённый текст','slug'=>'visible-text',
            'body'=>'Тест', 'status'=>'draft', 'museum_section_id'=>$my->id]);
        MuseumEntry::create(['type'=>'news','title'=>'Секретный заголовок','slug'=>'secret-text',
            'body'=>'Чужой материал', 'status'=>'draft', 'museum_section_id'=>$foreign->id]);
        $role = MoonshineUserRole::query()->where('name','Editor')->firstOrFail();
        $editor = MoonshineUser::factory()->create(['moonshine_user_role_id'=>$role->id]);
        $my->editors()->attach($editor->id);
        $this->actingAs($editor,'moonshine');

        $endpoint='/admin/resource/museum-entry-resource/museum-entry-index-page';
        $this->get($endpoint)->assertOk()->assertSee('Разрешённый текст')
            ->assertDontSee('Секретный заголовок');
        $this->get($endpoint.'?'.http_build_query([
            'filter'=>['museum_section_id'=>$my->id.' OR 1=1--'],
        ]))->assertOk()->assertDontSee('Секретный заголовок')
            ->assertDontSee('Разрешённый текст');
        $this->get($endpoint.'?'.http_build_query(['search'=>"' OR 1=1 --"]))
            ->assertOk()->assertDontSee('Секретный заголовок');
        $this->assertSame(2, MuseumEntry::count());
        $this->get('/admin/museum-entries/'.($foreign->id.' OR 1=1--').'/preview')
            ->assertNotFound();
    }
}
