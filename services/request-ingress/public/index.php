<?php
declare(strict_types=1);
// Dedicated ingress host, NOT the static web host; Nginx enforces mTLS on /internal/.
header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store');
header('X-Content-Type-Options: nosniff');
header('Referrer-Policy: no-referrer');
function reply(int $status,array $data): never {
 http_response_code($status);
 echo json_encode($data,JSON_THROW_ON_ERROR|JSON_UNESCAPED_UNICODE);exit;
}
function cfg(string $k): string {return trim((string)getenv($k));}
function input(): array {
 if((int)($_SERVER['CONTENT_LENGTH']??0)>8192) reply(413,['error'=>'too_large']);
 if(!str_starts_with(strtolower((string)($_SERVER['CONTENT_TYPE']??'')),'application/json'))
  reply(415,['error'=>'media_type']);
 $s=file_get_contents('php://input',false,null,0,8193);
 if(!is_string($s)||strlen($s)>8192) reply(413,['error'=>'too_large']);
 try {$v=json_decode($s,true,12,JSON_THROW_ON_ERROR);}
 catch(Throwable){reply(422,['error'=>'invalid']);}
 if(!is_array($v)||array_is_list($v)) reply(422,['error'=>'invalid']);
 return $v;
}
function store(): PDO {
 $path=cfg('MUSEUM_INGRESS_DB');
 if($path===''||$path[0]!=='/'||!is_dir(dirname($path))) throw new RuntimeException('db');
 umask(0077);
 $db=new PDO('sqlite:'.$path,null,null,[PDO::ATTR_ERRMODE=>PDO::ERRMODE_EXCEPTION]);
 $db->exec('PRAGMA busy_timeout=5000;PRAGMA journal_mode=WAL;PRAGMA synchronous=FULL');
 $db->exec('CREATE TABLE IF NOT EXISTS inbox(id TEXT PRIMARY KEY,envelope TEXT NOT NULL,created_at INTEGER NOT NULL)');
 $db->exec('CREATE TABLE IF NOT EXISTS limits(fingerprint TEXT,bucket INTEGER,hits INTEGER,PRIMARY KEY(fingerprint,bucket))');
 $db->exec('CREATE TABLE IF NOT EXISTS receipts(client_id TEXT PRIMARY KEY,request_id TEXT NOT NULL,body_hash TEXT NOT NULL,created_at INTEGER NOT NULL)');
 if(is_file($path)) chmod($path,0600);
 return $db;
}
function sanitize(array $v): array {
 $kind=$v['kind']??null;
 if(!in_array($kind,['feedback','excursion'],true)) reply(422,['error'=>'invalid']);
 $keys=['kind','name','email','message','consent','website','client_id'];
 if($kind==='excursion') array_push($keys,'date','group_size');
 foreach(array_keys($v) as $k) if(!in_array($k,$keys,true)) reply(422,['error'=>'invalid']);
 if(($v['website']??'')!=='') reply(202,['status'=>'received']); // bot honeypot
 $name=$v['name']??null;$email=$v['email']??null;
 $message=$v['message']??null;$consent=$v['consent']??null;
 if(!is_string($name)||!is_string($email)||!is_string($message)||!is_string($consent)
  ||cfg('MUSEUM_CONSENT_VERSION')===''||$consent!==cfg('MUSEUM_CONSENT_VERSION')
  ||trim($name)===''||trim($message)===''||mb_strlen($name)>100||mb_strlen($message)>1200
  ||strlen($email)>254||filter_var($email,FILTER_VALIDATE_EMAIL)===false
  ||preg_match('/[\x00-\x1F\x7F]/',$email)) reply(422,['error'=>'invalid']);
 $data=['kind'=>$kind,'name'=>trim($name),'email'=>$email,'message'=>trim($message),'consent'=>$consent];
 if($kind==='excursion'){
  $date=$v['date']??null;$group=$v['group_size']??null;
  $parts=is_string($date)?date_parse_from_format('!Y-m-d',$date):null;
  if(!is_string($date)||!preg_match('/^\d{4}-\d{2}-\d{2}$/D',$date)
   ||!is_array($parts)||$parts['error_count']!==0||$parts['warning_count']!==0
   ||!is_int($group)||$group<1||$group>100) reply(422,['error'=>'invalid']);
  $data['date']=$date;$data['group_size']=$group;
 }
 return $data;
}
try {
 $path=parse_url((string)($_SERVER['REQUEST_URI']??''),PHP_URL_PATH);
 $method=$_SERVER['REQUEST_METHOD']??'';
 if($path==='/health'&&$method==='GET') {store();reply(200,['status'=>'ok']);}
 if($path==='/v1/requests'&&$method==='OPTIONS') {
  $origin=cfg('MUSEUM_ALLOWED_ORIGIN');
  if($origin===''||($_SERVER['HTTP_ORIGIN']??'')!==$origin) reply(403,['error'=>'forbidden']);
  header('Access-Control-Allow-Origin: '.$origin);header('Access-Control-Allow-Methods: POST, OPTIONS');
  header('Access-Control-Allow-Headers: Content-Type');header('Vary: Origin');reply(204,[]);
 }
 if($path==='/v1/requests'&&$method==='POST'){
  $origin=cfg('MUSEUM_ALLOWED_ORIGIN');
  if($origin===''||($_SERVER['HTTP_ORIGIN']??'')!==$origin) reply(403,['error'=>'forbidden']);
  header('Access-Control-Allow-Origin: '.$origin);header('Vary: Origin');
  $submitted=input();
  $clientId=$submitted['client_id']??null;
  if($clientId!==null && (!is_string($clientId)||!preg_match('/^[a-f0-9]{32}$/D',$clientId)))
   reply(422,['error'=>'invalid']);
  $data=sanitize($submitted);
  $pub=base64_decode(cfg('MUSEUM_INGRESS_PUBLIC_KEY'),true);
  if($pub===false||strlen($pub)!==SODIUM_CRYPTO_BOX_PUBLICKEYBYTES||strlen(cfg('MUSEUM_RATE_SECRET'))<32)
   reply(503,['error'=>'unavailable']);
  $ipHash=hash_hmac('sha256',(string)($_SERVER['REMOTE_ADDR']??''),cfg('MUSEUM_RATE_SECRET'));
  $bucket=intdiv(time(),60);$id=bin2hex(random_bytes(16));
  $encrypted=base64_encode(sodium_crypto_box_seal(json_encode($data,JSON_THROW_ON_ERROR|JSON_UNESCAPED_UNICODE),$pub));
  $digest=hash_hmac('sha256',json_encode($data,JSON_THROW_ON_ERROR|JSON_UNESCAPED_UNICODE),cfg('MUSEUM_RATE_SECRET'));
  $db=store();$db->exec('BEGIN IMMEDIATE');
  try {
   $db->prepare('DELETE FROM receipts WHERE created_at<?')->execute([time()-604800]);
   if($clientId!==null){
    $q=$db->prepare('SELECT request_id,body_hash FROM receipts WHERE client_id=?');
    $q->execute([$clientId]);$existing=$q->fetch(PDO::FETCH_ASSOC);
    if($existing!==false){
     $db->exec('COMMIT');
     if(!hash_equals($existing['body_hash'],$digest)) reply(409,['error'=>'conflict']);
     reply(202,['status'=>'received','request_id'=>$existing['request_id']]);
    }
   }
   $db->prepare('DELETE FROM limits WHERE bucket<?')->execute([$bucket-1440]);
   $db->prepare('INSERT INTO limits(fingerprint,bucket,hits) VALUES(?,?,1) ON CONFLICT(fingerprint,bucket) DO UPDATE SET hits=hits+1')->execute([$ipHash,$bucket]);
   $q=$db->prepare('SELECT hits FROM limits WHERE fingerprint=? AND bucket=?');$q->execute([$ipHash,$bucket]);
   if((int)$q->fetchColumn()>5){$db->exec('COMMIT');reply(429,['error'=>'limited']);}
   if((int)$db->query('SELECT COUNT(*) FROM inbox')->fetchColumn()>=5000){$db->exec('COMMIT');reply(503,['error'=>'full']);}
   $db->prepare('INSERT INTO inbox(id,envelope,created_at) VALUES(?,?,?)')->execute([$id,$encrypted,time()]);
   if($clientId!==null)
    $db->prepare('INSERT INTO receipts(client_id,request_id,body_hash,created_at) VALUES(?,?,?,?)')->execute([$clientId,$id,$digest,time()]);
   $db->exec('COMMIT');
  }catch(Throwable $e){$db->exec('ROLLBACK');throw $e;}
  reply(202,['status'=>'received','request_id'=>$id]);
 }
 if(str_starts_with((string)$path,'/internal/')){
  $token=cfg('MUSEUM_INTERNAL_TOKEN');
  if(strlen($token)<32||!hash_equals('Bearer '.$token,(string)($_SERVER['HTTP_AUTHORIZATION']??'')))
   reply(403,['error'=>'forbidden']);
  $db=store();
  if($path==='/internal/pull'&&$method==='GET')
   reply(200,['items'=>$db->query('SELECT id,envelope FROM inbox ORDER BY created_at,id LIMIT 20')->fetchAll(PDO::FETCH_ASSOC)]);
  if($path==='/internal/ack'&&$method==='POST'){
   $ids=input()['ids']??null;
   if(!is_array($ids)||count($ids)<1||count($ids)>20) reply(422,['error'=>'invalid']);
   foreach($ids as $id) if(!is_string($id)||!preg_match('/^[a-f0-9]{32}$/D',$id))
    reply(422,['error'=>'invalid']);
   $db->beginTransaction();$del=$db->prepare('DELETE FROM inbox WHERE id=?');
   foreach(array_unique($ids) as $id)$del->execute([$id]);
   $db->commit();reply(200,['status'=>'acknowledged']);
  }
 }
 reply(404,['error'=>'not_found']);
}catch(Throwable){reply(503,['error'=>'unavailable']);}
