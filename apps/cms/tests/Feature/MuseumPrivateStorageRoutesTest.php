<?php

namespace Tests\Feature;

use Illuminate\Support\Facades\Route;
use Illuminate\Support\Facades\Storage;
use Tests\TestCase;

final class MuseumPrivateStorageRoutesTest extends TestCase
{
    public function test_cms_private_disk_cannot_register_public_signed_get_or_put_routes(): void
    {
        $this->assertSame('local', config('filesystems.default'));
        $this->assertSame(storage_path('app/private'), config('filesystems.disks.local.root'));
        $this->assertFalse(config('filesystems.disks.local.serve'));
        $this->assertFalse(Route::has('storage.local'));
        $this->assertFalse(Route::has('storage.local.upload'));
        $this->assertSame('local', config('filesystems.default'));
    }

    public function test_private_originals_are_not_served_by_framework_storage_url_even_to_admin(): void
    {
        Storage::fake('local');
        Storage::disk('local')->put('museum/media/private-original.webp', 'DO_NOT_EXPOSE');
        $this->get('/storage/museum/media/private-original.webp')->assertNotFound();
        $this->put('/storage/museum/media/private-original.webp', ['body' => 'overwrite'])->assertNotFound();
        $this->assertSame('DO_NOT_EXPOSE',
            Storage::disk('local')->get('museum/media/private-original.webp'));
    }
}
