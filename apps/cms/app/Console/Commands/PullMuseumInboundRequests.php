<?php
declare(strict_types=1);
namespace App\Console\Commands;
use App\Models\MuseumInboundRequest;
use Illuminate\Console\Command;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Http;
use Throwable;

final class PullMuseumInboundRequests extends Command {
    protected $signature = 'museum:pull-requests';
    protected $description = 'Import sealed public inquiries through authenticated private mTLS (disabled by default)';

    public function handle(): int {
        if (!config('museum_requests.enabled')) {
            $this->warn('Import disabled: customer privacy and network approval required.');
            return self::FAILURE;
        }
        $url = rtrim((string)config('museum_requests.url'), '/');
        $token = (string)config('museum_requests.token');
        $secret = base64_decode((string)config('museum_requests.secret_key'), true);
        $cert = (string)config('museum_requests.tls_cert');
        $key = (string)config('museum_requests.tls_key');
        $ca = (string)config('museum_requests.tls_ca');
        if (!str_starts_with($url, 'https://') || strlen($token)<32 ||
            $secret===false || strlen($secret)!==SODIUM_CRYPTO_BOX_SECRETKEYBYTES ||
            !is_file($cert) || !is_file($key) || !is_file($ca) ||
            (string)config('museum_requests.consent_version')==='') {
            $this->error('Private ingress configuration incomplete.');
            return self::FAILURE;
        }
        // File paths are private server-side certs; never included in public build.
        $options = ['cert'=>$cert, 'ssl_key'=>$key, 'verify'=>$ca, 'allow_redirects'=>false, 'timeout'=>15];
        $pair = sodium_crypto_box_keypair_from_secretkey_and_publickey(
            $secret, sodium_crypto_box_publickey_from_secretkey($secret));
        try {
            $client = Http::withToken($token)->withOptions($options)->acceptJson();
            $response = $client->get($url.'/internal/pull');
            if (!$response->successful()) throw new \RuntimeException('pull HTTP error');
            $items = $response->json('items');
            if (!is_array($items) || count($items)>20) throw new \RuntimeException('invalid batch');
            $ids = [];
            foreach ($items as $item) {
                $id = $item['id']??null;
                $sealed = isset($item['envelope']) && is_string($item['envelope'])
                    ? base64_decode($item['envelope'], true) : false;
                if (!is_string($id) || !preg_match('/^[a-f0-9]{32}$/D',$id) ||
                    $sealed===false) throw new \RuntimeException('invalid item');
                $clear = sodium_crypto_box_seal_open($sealed,$pair);
                if ($clear===false) throw new \RuntimeException('decrypt failure');
                $p = json_decode($clear, true, 12, JSON_THROW_ON_ERROR);
                if (!is_array($p) || !in_array($p['kind']??null,['feedback','excursion'],true)
                    || !is_string($p['name']??null) || !is_string($p['email']??null)
                    || !is_string($p['message']??null)
                    || ($p['consent']??null)!==config('museum_requests.consent_version')
                    || trim($p['name'])==='' || mb_strlen($p['name'])>100
                    || trim($p['message'])==='' || mb_strlen($p['message'])>1200
                    || !filter_var($p['email'], FILTER_VALIDATE_EMAIL)
                    || (($p['kind']==='excursion') && (
                        !isset($p['date'],$p['group_size']) || !is_string($p['date'])
                        || !preg_match('/^\d{4}-\d{2}-\d{2}$/D', $p['date'])
                        || !is_int($p['group_size']) || $p['group_size']<1 || $p['group_size']>100
                    ))) throw new \RuntimeException('invalid payload');
                // Duplicate deliveries are safe; acknowledge ONLY after durable DB commit.
                DB::transaction(static function () use ($id,$p): void {
                    MuseumInboundRequest::query()->firstOrCreate(
                        ['external_id'=>$id], ['kind'=>$p['kind'],'payload'=>$p,'received_at'=>now()]);
                });
                $ids[]=$id;
            }
            if ($ids!==[]) {
                $ack = $client->post($url.'/internal/ack',['ids'=>$ids]);
                if (!$ack->successful()) throw new \RuntimeException('ack failed');
            }
            $this->info('Imported/acknowledged: '.count($ids));
            return self::SUCCESS;
        } catch (Throwable) {
            // Do not print exception text: it may include remote body/credentials.
            $this->error('Private inbox pull failed; unacknowledged items remain queued.');
            return self::FAILURE;
        } finally {
            sodium_memzero($secret);
        }
    }
}
