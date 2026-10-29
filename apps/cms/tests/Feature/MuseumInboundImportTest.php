<?php
declare(strict_types=1);
namespace Tests\Feature;

use App\Models\MuseumInboundRequest;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Http;
use Tests\TestCase;

final class MuseumInboundImportTest extends TestCase {
    use RefreshDatabase;
    private array $paths=[];

    protected function tearDown(): void {
        foreach($this->paths as $path) @unlink($path);
        parent::tearDown();
    }
    private function configure(): string {
        $pair=sodium_crypto_box_keypair();
        $secret=sodium_crypto_box_secretkey($pair);
        foreach(['cert','key','ca'] as $key){
            $file=tempnam(sys_get_temp_dir(),'musbread-qa-');
            file_put_contents($file,'SYNTHETIC-CERT-FOR-FAKE-HTTP-ONLY');
            $this->paths[]=$file;
            config()->set("museum_requests.tls_{$key}",$file);
        }
        config()->set('museum_requests.enabled',true);
        config()->set('museum_requests.url','https://ingress.internal');
        config()->set('museum_requests.token',str_repeat('s',64));
        config()->set('museum_requests.secret_key',base64_encode($secret));
        config()->set('museum_requests.consent_version','test-v1');
        return $pair;
    }
    private function sealed(array $payload,string $pair): array {
        return ['id'=>str_repeat('a',32), 'envelope'=>base64_encode(sodium_crypto_box_seal(
            json_encode($payload,JSON_THROW_ON_ERROR|JSON_UNESCAPED_UNICODE),
            sodium_crypto_box_publickey($pair)))];
    }
    private function payload(): array {
        return ['kind'=>'feedback','name'=>'Тестовый посетитель','email'=>'visitor@example.org',
            'message'=>'Тестовое сообщение','consent'=>'test-v1'];
    }

    public function test_import_disabled_by_default(): void {
        config()->set('museum_requests.enabled',false);
        Http::fake();
        $this->artisan('museum:pull-requests')->assertExitCode(1);
        Http::assertNothingSent();
        $this->assertDatabaseCount('museum_inbound_requests',0);
    }
    public function test_encrypted_durable_import_and_idempotent_duplicate(): void {
        $pair=$this->configure();
        $item=$this->sealed($this->payload(),$pair);
        Http::fake([
            'https://ingress.internal/internal/pull'=>Http::response(['items'=>[$item]],200),
            'https://ingress.internal/internal/ack'=>Http::response(['status'=>'acknowledged'],200),
        ]);
        $this->artisan('museum:pull-requests')->assertExitCode(0);
        $this->artisan('museum:pull-requests')->assertExitCode(0); // ack lost -> replay
        $this->assertDatabaseCount('museum_inbound_requests',1);
        $row=MuseumInboundRequest::firstOrFail();
        $this->assertSame($this->payload(),$row->payload);
        $cipher=DB::table('museum_inbound_requests')->value('payload');
        $this->assertStringNotContainsString('visitor@example.org',$cipher);
        $this->assertStringNotContainsString('Тестовый',$cipher);
        Http::assertSentCount(4);
    }
    public function test_tampered_envelope_fails_closed_without_ack_or_storage(): void {
        $this->configure();
        Http::fake([
            'https://ingress.internal/internal/pull'=>Http::response(['items'=>[
                ['id'=>str_repeat('b',32),'envelope'=>base64_encode('invalid sealed body')],
            ]],200),
        ]);
        $this->artisan('museum:pull-requests')->assertExitCode(1);
        $this->assertDatabaseCount('museum_inbound_requests',0);
        Http::assertSentCount(1);
    }
    public function test_ack_failure_does_not_remove_imported_record(): void {
        $pair=$this->configure();
        Http::fake([
            'https://ingress.internal/internal/pull'=>Http::response(['items'=>[
                $this->sealed($this->payload(),$pair)]],200),
            'https://ingress.internal/internal/ack'=>Http::response(['error'=>'unavailable'],503),
        ]);
        $this->artisan('museum:pull-requests')->assertExitCode(1);
        $this->assertDatabaseCount('museum_inbound_requests',1);
    }
}
