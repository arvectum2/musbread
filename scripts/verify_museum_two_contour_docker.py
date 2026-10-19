#!/usr/bin/env python3
"""CP-ARCH-01: reproducible local TWO-NETWORK transfer acceptance.

No connection to the museum or production DNS. This deliberately uses a
PRIVATE PHP 8.4 transfer surrogate, NOT the Laravel editor application. It
checks the security boundary needed for later customer-network commissioning:
private sender -> approved dual-network courier -> read-only public receiver.
Only a source-verified small slice of the actual Next export is transferred.
Existing full-site SHA256 release/rollback tests remain separate.
"""
from __future__ import annotations
import hashlib,json,os,shutil,socket,subprocess,sys,tarfile,tempfile,time,uuid
from pathlib import Path
from urllib.request import urlopen
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from verify_static_transfer import make_manifest,verify_manifest
LOCAL=ROOT/'.local_archive'
PORT=int(os.getenv('MUSBREAD_TWO_CONTOUR_QA_PORT','18089'))
if not (1024 <= PORT <= 65535):raise SystemExit('Only high localhost ports accepted')

def run(*args,check=True,timeout=55):
 p=subprocess.run(['docker',*map(str,args)],text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=timeout)
 if check and p.returncode:
  raise RuntimeError('Docker operation failed: '+str(args[:4])+' '+p.stderr[-500:])
 return p

def sha(data):return hashlib.sha256(data).hexdigest()

def assert_error(action,description):
 try: action()
 except ValueError:return
 raise AssertionError('Negative test failed: '+description)

def assert_http(url,expect,content=None):
 with urlopen(url,timeout=8) as r:
  if r.status!=200:raise AssertionError('Unexpected HTTP status '+str(r.status))
  raw=r.read()
  if content is not None and raw!=content:
   raise AssertionError('Wrong public response bytes '+url)
  return raw

def test(source_output:Path|None=None,required_news:str|None=None):
 src=source_output if source_output is not None else ROOT/'apps/web/out'
 if source_output is not None and (not src.is_dir() or src.is_symlink()):
  raise ValueError('Isolated source build is missing or unsafe')
 if required_news is not None and (not required_news.startswith('news/') or not required_news.endswith('/index.html') or '..' in Path(required_news).parts):
  raise ValueError('Expected queued CMS publication route is invalid')
 files=['index.html','robots.txt','sitemap.xml','novosty/index.html']
 photo=next(iter(sorted((src/'media/museum-source').glob('*.webp'))),None)
 if not photo:raise RuntimeError('Missing source-verified local museum WebP')
 files.append('media/museum-source/'+photo.name)
 if required_news is not None: files.append(required_news)
 for name in files:
  if not (src/name).is_file():raise RuntimeError('Build museum site before testing: '+name)
 tag=uuid.uuid4().hex[:9]
 private_network='musbread-qa-private-'+tag
 public_network='musbread-qa-public-'+tag
 cms='musbread-qa-cms-'+tag
 relay='musbread-qa-relay-'+tag
 public='musbread-qa-public-'+tag
 volume='musbread-qa-public-releases-'+tag
 containers=[public,relay,cms]
 networks=[public_network,private_network]
 home=LOCAL/('qa-two-contours-'+tag)
 home.mkdir(mode=0o700)
 evidence={}
 try:
  sender=home/'sender';sender.mkdir()
  for name in files:
   dst=sender/name;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src/name,dst)
  trusted=home/'out-of-band-trusted-inventory.json'
  inventory=make_manifest(sender,trusted)
  private=home/'cms-private';private.mkdir(mode=0o700)
  archive=private/'export.tar'
  with tarfile.open(archive,'w') as tf:
   for name in files:tf.add(sender/name,arcname=name,recursive=False)
  (private/'index.html').write_text('PRIVATE-CMS-TRANSFER-HEALTH: cannot leak to public\n',encoding='utf-8')
  receiving=home/'receiver';receiving.mkdir(mode=0o700)
  # Public and backend must have NO shared Docker network, and CMS must have
  # no host published port. Only the relay is on both physically distinct nets.
  run('network','create','--internal',private_network)
  run('network','create',public_network)
  run('volume','create',volume)
  run('run','-d','--rm','--name',cms,'--network',private_network,
      '--mount',f'type=bind,source={private},target=/srv/private,readonly',
      'php:8.4-cli','php','-S','0.0.0.0:8081','-t','/srv/private')
  run('run','-d','--rm','--name',relay,'--network',private_network,
      '--mount',f'type=bind,source={receiving},target=/handoff',
      '--mount',f'type=volume,source={volume},target=/published',
      'alpine:3.20','sleep','3600')
  run('network','connect',public_network,relay)
  for i in range(12):
   ready=run('exec',relay,'wget','-q','--timeout=2','-O','/dev/null','http://'+cms+':8081/index.html',check=False,timeout=5)
   if ready.returncode==0:break
   time.sleep(.5)
  else:raise RuntimeError('Private CMS channel was not reachable to the authorized relay')
  # Transfer flows inside a Docker-only private network via the courier.
  got=run('exec',relay,'wget','-q','--timeout=15','-O','/handoff/incoming.tar','http://'+cms+':8081/export.tar',timeout=45)
  incoming=receiving/'incoming.tar'
  if not incoming.is_file() or sha(incoming.read_bytes())!=sha(archive.read_bytes()):
   raise AssertionError('Private channel transport byte checksum mismatch')
  staged=home/'public-release-staging';staged.mkdir(mode=0o700)
  with tarfile.open(incoming,'r') as tf:
   members=tf.getmembers()
   if {m.name for m in members}!=set(files) or any(not m.isfile() for m in members):
    raise RuntimeError('Untrusted archive contains unexpected members')
   for m in members:
    if m.name.startswith('/') or '..' in Path(m.name).parts:raise RuntimeError('Archive traversal')
    dest=staged/m.name;dest.parent.mkdir(parents=True,exist_ok=True)
    with tf.extractfile(m) as source, dest.open('wb') as output:shutil.copyfileobj(source,output)
  expected=verify_manifest(staged,trusted)
  if expected!=inventory or len(expected['files'])!=len(files):raise AssertionError('Trusted manifest mismatch')
  # Attack: altered transfer must be rejected before public activation.
  probe=staged/'index.html';original=probe.read_bytes();probe.write_bytes(original+b'TAMPERED')
  assert_error(lambda:verify_manifest(staged,trusted),'tampered remote static HTML must fail closed')
  probe.write_bytes(original)
  verify_manifest(staged,trusted)
  # Attack: added private PHP / secret must fail inventory verification.
  evil=staged/'admin.php';evil.write_text('<?php echo "no"; ?>')
  assert_error(lambda:verify_manifest(staged,trusted),'new executable on public server must fail closed')
  evil.unlink();verify_manifest(staged,trusted)
  # Docker Desktop macOS host bind-mounted *symlink replacements* are not
  # always immediately visible inside the VM. Keep immutable release paths
  # and the `current` pointer inside a real Linux Docker named volume.
  # Only the authorized courier has RW access; public Nginx gets RO mount.
  release_id=sha(trusted.read_bytes())[:16]
  run('exec',relay,'mkdir','-p','/published/releases/'+release_id)
  run('exec',relay,'tar','-xf','/handoff/incoming.tar','-C','/published/releases/'+release_id)
  for name in files:
   observed=run('exec',relay,'sha256sum','/published/releases/'+release_id+'/'+name).stdout.split()[0]
   if observed!=inventory['files'][name]:
    raise AssertionError('Copied bytes in Linux volume do not match approved sidecar: '+name)
  run('exec',relay,'ln','-s','releases/'+release_id,'/published/current')
  # Real Nginx public HTTP, image files and no private backend mounts.
  conf=home/'public-nginx.conf'
  conf.write_text('''worker_processes 1;
events { worker_connections 64; }
http { include /etc/nginx/mime.types; default_type application/octet-stream;
 server { listen 8080; server_name localhost; root /srv/public/current;
 add_header X-Musbread-Two-Contour-QA "isolated" always;
 location ~* ^/(admin|api|vendor|storage|database|bootstrap|config|private)(/|$) { return 404; }
 location ~* \\.(php|env|sql|sqlite|bak|log)(/|$) { return 404; }
 location ~ /\\. { return 404; }
 location / { try_files $uri/index.html $uri =404; }
 }}
''')
  run('run','-d','--rm','--name',public,'--network',public_network,
      '-p',f'127.0.0.1:{PORT}:8080',
      '--mount',f'type=volume,source={volume},target=/srv/public,readonly',
      '--mount',f'type=bind,source={conf},target=/etc/nginx/nginx.conf,readonly',
      'nginx:stable-alpine','nginx','-g','daemon off;')
  for i in range(12):
   try:
    with urlopen(f'http://127.0.0.1:{PORT}/robots.txt',timeout=2) as r:
     if r.status==200 and r.headers['X-Musbread-Two-Contour-QA']=='isolated':break
   except (OSError,TimeoutError):time.sleep(.5)
  else:raise AssertionError('Local Nginx did not become reachable')
  # Actual Docker introspection: no public-to-CMS network/shared mounts.
  raw=json.loads(run('inspect',cms,relay,public).stdout)
  for container in raw:
   nets=set(container['NetworkSettings']['Networks'])
   name=container['Name'].lstrip('/')
   if name==cms:
    if nets!={private_network} or container['NetworkSettings']['Ports'].get('8081/tcp'):
     raise AssertionError('Private CMS is reachable from the host/public network')
   elif name==relay:
    if nets!={private_network,public_network}:raise AssertionError('Relay network exception wrong')
   elif name==public:
    if nets!={public_network}:raise AssertionError('Public Nginx sees CMS network')
    mounts=container['Mounts']
    if (any(m['Source'] in (str(private),str(sender),str(receiving)) for m in mounts)
       or not any(m['Type']=='volume' and m['Name']==volume and not m['RW'] for m in mounts)):
     raise AssertionError('Public filesystem not read-only or contains private CMS files')
  # Deny direct traffic in both directions; relay is the sole network bridge.
  denied=run('exec',public,'wget','--timeout=2','--tries=1','-q','-O','/dev/null','http://'+cms+':8081/index.html',check=False,timeout=6)
  if denied.returncode==0:raise AssertionError('PUBLIC NGINX DIRECTLY REACHED PRIVATE CMS')
  cms_denied=run('exec',cms,'php','-r',"$x=@file_get_contents('http://"+public+":8080/index.html'); exit($x===false?0:1);",check=False,timeout=6)
  if cms_denied.returncode!=0:raise AssertionError('PRIVATE CMS DIRECTLY REACHED PUBLIC NGINX')
  # Public endpoints byte-for-byte match real museum original-site static.
  for name in files:
   path='/'+name
   body=assert_http(f'http://127.0.0.1:{PORT}'+path,200,original if name=='index.html' else (src/name).read_bytes())
  for private_path in ('/admin','/private/index.html','/storage/.env','/index.php','/api','/vendor/autoload.php'):
   try:
    urlopen(f'http://127.0.0.1:{PORT}'+private_path,timeout=4)
   except Exception as exc:
    if getattr(exc,'code',None)!=404:
     raise AssertionError('Expected precise 404 for '+private_path+': '+str(exc))
   else:raise AssertionError('Sensitive path publicly reachable '+private_path)
  # A real queued CMS-export -> Next.js build must reach the public Docker
  # Nginx directly by its static URL, with editorial drafts absent.
  if required_news is not None:
   real_html=assert_http(f'http://127.0.0.1:{PORT}/'+required_news,200,(src/required_news).read_bytes())
   slug=Path(required_news).parts[1]
   if (slug.encode() not in real_html
       or b'qa-real-queue-draft-hidden' in real_html
       or b'qa-unapproved-draft-hidden' in real_html):
    raise AssertionError('Real queued publisher page missing, or draft leaked in Docker public HTTP')
  # Verify fallback release pointer switch uses original trusted checksum.
  live_pointer=run('exec',relay,'readlink','/published/current').stdout.strip()
  if live_pointer!='releases/'+release_id:
   raise AssertionError('Active public Linux-volume release pointer not verified')
  if not run('exec',public,'sh','-c','test ! -d /srv/private && test ! -e /srv/public/current/admin.php').returncode==0:
   raise AssertionError('Public container contains private CMS files')
  # Rehearse a SECOND *synthetic QA-only artifact version*, not a new editor
  # approval. The public Nginx stays running and sees a one-step atomic symlink
  # switch. A broken package MUST not affect the current live HTTP bytes.
  v2=home/'local-second-artifact';shutil.copytree(staged,v2)
  delta=b'\n<!-- isolated Docker rollback acceptance QA-only delta -->\n'
  (v2/'index.html').write_bytes(original+delta)
  trusted2=home/'second-trusted-manifest.json'
  make_manifest(v2,trusted2)
  tamper2=v2/'robots.txt'
  saved_robots=tamper2.read_bytes();tamper2.write_bytes(saved_robots+b'broken')
  assert_error(lambda:verify_manifest(v2,trusted2),'second changed release must never become active')
  if run('exec',relay,'readlink','/published/current').stdout.strip()!='releases/'+release_id:
   raise AssertionError('Malformed second package changed active Linux-volume pointer')
  if assert_http(f'http://127.0.0.1:{PORT}/index.html',200)!=original:
   raise AssertionError('Failed second package caused visible content change')
  tamper2.write_bytes(saved_robots)
  verify_manifest(v2,trusted2)
  release2_id=sha(trusted2.read_bytes())[:16]
  if release2_id==release_id:raise AssertionError('Second test artifact lacks distinct release ID')
  run('exec',relay,'mkdir','-p','/published/releases/'+release2_id)
  # Docker copies the approved five-file QA-only delta into its Linux volume;
  # the courier remains the only process with a RW release mount.
  run('cp',str(v2)+'/.',relay+':/published/releases/'+release2_id,timeout=30)
  for name,checksum in verify_manifest(v2,trusted2)['files'].items():
   observed=run('exec',relay,'sha256sum','/published/releases/'+release2_id+'/'+name).stdout.split()[0]
   if observed!=checksum:raise AssertionError('Second Linux-volume artifact checksum mismatch: '+name)
  def atomically_switch(release_name):
   tmp='/published/.current-'+tag+'.tmp'
   run('exec',relay,'ln','-s','releases/'+release_name,tmp)
   run('exec',relay,'mv','-Tf',tmp,'/published/current')
  atomically_switch(release2_id)
  if assert_http(f'http://127.0.0.1:{PORT}/index.html',200)!=original+delta:
   raise AssertionError('Verified new release not immediately visible via SAME live Nginx endpoint')
  atomically_switch(release_id)
  if assert_http(f'http://127.0.0.1:{PORT}/index.html',200)!=original:
   raise AssertionError('Atomic Linux-volume rollback did not restore original real museum HTML')
  if run('exec',relay,'readlink','/published/current').stdout.strip()!='releases/'+release_id:
   raise AssertionError('Restored Linux-volume release pointer not verified')
  for name,checksum in inventory['files'].items():
   observed=run('exec',relay,'sha256sum','/published/current/'+name).stdout.split()[0]
   if observed!=checksum:raise AssertionError('Rolled-back museum file checksum mismatch: '+name)
  evidence={'scenario':'CP-ARCH-01_ISOLATED_DOCKER_TRANSFER_SUBSET',
   'scope':('6 files including REAL Laravel database queued worker -> Next.js HTML' if required_news else '5 REAL Next.js static output files, private PHP transfer surrogate; NOT actual Laravel CMS publisher'),
   'private_cms_network_only':True,'public_nginx_network_only':True,
   'sole_two_network_courier':True,'cms_host_ports_published':0,
   'private_to_public_direct_access_denied':True,'public_to_private_direct_access_denied':True,
   'courier_sourced_private_package_over_real_Docker_network':True,
   'trusted_manifest_outside_package':True,
   'receiver_files_sha256_verified':len(files),
   'queue_built_news_visible_by_HTTP':required_news is not None,
   'modified_static_html_rejected':True,'injected_php_file_rejected':True,
   'public_files_HTTP_200_byte_identical':len(files),
   'public_sensitive_paths_HTTP_404':6,
   'public_volume_contains_private_cms':False,
   'public_release_mount_read_only_Docker_named_volume':True,
   'only_authorized_courier_can_switch_Linux_volume_release':True,
   'tampered_second_release_blocked_before_switch':True,
   'verified_second_test_release_HTTP_visible':True,
   'atomic_symlink_rollback_HTTP_restored_original':True,
   'synthetic_second_artifact_NOT_editorial_CMS_approval':True,
   'isolated_loopback_hostport':PORT,
   'prod_network_and_SSL_tested':False}
  print('MUSEUM_DOCKER_TWO_CONTOUR_QA_PASS '+json.dumps(evidence,ensure_ascii=False,sort_keys=True),flush=True)
  return evidence
 finally:
  for name in containers:run('rm','-f',name,check=False,timeout=12)
  for name in networks:run('network','rm',name,check=False,timeout=12)
  run('volume','rm',volume,check=False,timeout=12)
  shutil.rmtree(home,ignore_errors=True)

if __name__=='__main__':test()
