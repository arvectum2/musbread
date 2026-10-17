<?php

declare(strict_types=1);

namespace App\Console\Commands;

use Illuminate\Console\Command;
use Illuminate\Support\Facades\Cache;

/**
 * TZ-217: Check the existing Laravel cache store and atomic publication locks
 * without changing any museum content, users or public release files.
 */
final class CheckMuseumCache extends Command
{
    protected $signature = 'museum:cache-check
        {--require-shared : Fail if the configured store is not suitable for multiple workers}';

    protected $description = 'Verify configured Laravel cache put/get and exclusive locks, without publishing';

    public function handle(): int
    {
        $store = (string) config('cache.default');
        // A file store may be sufficient on one server but cannot be assumed
        // shared by workers on different museum servers.
        if ($this->option('require-shared')
            && ! in_array($store, ['database', 'redis', 'memcached'], true)) {
            $this->error('Cache store is not an approved multi-worker shared type.');
            return self::FAILURE;
        }

        $nonce = bin2hex(random_bytes(16));
        $key = 'musbread:cache-check:value:'.$nonce;
        $lockKey = 'musbread:cache-check:lock:'.$nonce;
        $first = null;
        $second = null;
        $firstHeld = false;
        $secondHeld = false;

        try {
            Cache::put($key, $nonce, 30);
            if (Cache::get($key) !== $nonce) {
                $this->error('Cache value could not be read back.');
                return self::FAILURE;
            }

            $first = Cache::lock($lockKey, 30);
            $second = Cache::lock($lockKey, 30);
            if (! $first->get()) {
                $this->error('Cache lock cannot be acquired.');
                return self::FAILURE;
            }
            $firstHeld = true;
            // A second independent owner MUST NOT enter the publication
            // critical section while the first owner holds the lock.
            if ($second->get()) {
                $secondHeld = true;
                $this->error('Cache lock is not exclusive.');
                return self::FAILURE;
            }

            $first->release();
            $firstHeld = false;
            if (! $second->get()) {
                $this->error('Cache lock cannot be acquired after release.');
                return self::FAILURE;
            }
            $secondHeld = true;

            $this->info('CACHE OK (store: '.$store.'; read/write and exclusive locks verified)');
            return self::SUCCESS;
        } catch (\Throwable $error) {
            // Never expose database DSNs, cache passwords or raw paths.
            $this->error('Cache test failed ('.class_basename($error).').');
            return self::FAILURE;
        } finally {
            if ($secondHeld && $second !== null) $second->release();
            if ($firstHeld && $first !== null) $first->release();
            try {
                Cache::forget($key);
            } catch (\Throwable) {
                // The failed check already returned FAILURE; do not expose
                // store configuration through a cleanup exception.
            }
        }
    }
}
