#!/usr/bin/env python3
"""True Laravel DATABASE QUEUE -> isolated CMS snapshot -> Next static QA.

All artifacts and SQLite are disposable under ArvectumSSD .local_archive.
No production CMS DB, no actual museum credentials, no network to museum.
A later Docker courier checks/serves the resulting static HTML.
"""
from __future__ import annotations
import base64,hashlib,json,os,secrets,shutil,subprocess,sys,tempfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CMS=ROOT/'apps/cms';WEB=ROOT/'apps/web'
MOUNT=ROOT/'.local_archive'
ENTRY='qa-real-laravel-queue-news'

def execute(args,cwd,env,timeout=150):
 p=subprocess.run(args,cwd=cwd,env=env,text=True,capture_output=True,timeout=timeout)
 if p.returncode:
  # Never print raw file contents, DB secrets or credentials.
  raise RuntimeError('Local QA command failed '+str(args[:4])+' status '+str(p.returncode)+' output '+(p.stderr+p.stdout)[-1100:])
 return p.stdout

def main():
 MOUNT.mkdir(exist_ok=True)
 with tempfile.TemporaryDirectory(prefix='queue-next-docker-',dir=MOUNT) as base:
  workspace=Path(base);db=workspace/'private.sqlite';db.touch()
  stage=workspace/'private-export';stage.mkdir(mode=0o700)
  env=dict(os.environ)
  env.update({'APP_ENV':'local','APP_DEBUG':'false',
   'APP_KEY':'base64:'+base64.b64encode(secrets.token_bytes(32)).decode(),
   'DB_CONNECTION':'sqlite','DB_DATABASE':str(db),'DB_URL':'',
   'QUEUE_CONNECTION':'database','CACHE_STORE':'database','SESSION_DRIVER':'database',
   'MUSEUM_ENABLE_APPROVAL_QUEUE':'false','MUSEUM_USE_PUBLISH_QUEUE':'true',
   'MUSEUM_QUEUED_EXPORT_STAGING_DIR':str(stage),'MAIL_MAILER':'array',
   'NEXT_TELEMETRY_DISABLED':'1'})
  if (CMS/'bootstrap/cache/config.php').exists():
   raise RuntimeError('Unexpected cached production Laravel config, refusing ephemeral DB QA')
  execute(['php','artisan','migrate','--force','--no-ansi'],CMS,env)
  create='''require "vendor/autoload.php"; $app=require "bootstrap/app.php";
  $app->make(\\Illuminate\\Contracts\\Console\\Kernel::class)->bootstrap();
  \\App\\Models\\MuseumEntry::create(["type"=>"news","slug"=>"qa-real-laravel-queue-news",
  "title"=>"QA: Новость из настоящей очереди Laravel", "body"=>"<p>QA тест изолированного обработчика очереди.</p>","status"=>"published"]);
  \\App\\Models\\MuseumEntry::create(["type"=>"news","slug"=>"qa-real-queue-draft-hidden",
  "title"=>"QA: Закрытый черновик", "body"=>"<p>Не выгружать.</p>","status"=>"draft"]);
  \\App\\Models\\MuseumEvent::create(["slug"=>"qa-real-queue-test-event","title"=>"QA: Тестовое событие очереди",
  "category"=>"museum", "starts_at"=>"2026-10-19", "excerpt"=>"QA проверка очереди.",
  "body"=>"Тестовый материал для статического маршрута", "status"=>"published"]);'''
  execute(['php','-r',create],CMS,env)
  queued=execute(['php','artisan','museum:queue-export','--no-ansi'],CMS,env)
  if 'Queued museum publication #' not in queued:
   raise RuntimeError('The REAL Laravel publication command did not enqueue an actual job')
  before=hashlib.sha256((WEB/'src/data/published.json').read_bytes()).hexdigest()
  execute(['php','artisan','queue:work','database','--queue=museum-publish',
           '--once','--tries=1','--timeout=120','--no-ansi'],CMS,env,timeout=180)
  check='''require "vendor/autoload.php"; $app=require "bootstrap/app.php";
    $app->make(\\Illuminate\\Contracts\\Console\\Kernel::class)->bootstrap();
    $runs=\\App\\Models\\MuseumPublicationRun::all()->map(fn($r)=>["status"=>$r->status,
       "attempts"=>$r->attempts,"sha256"=>$r->snapshot_sha256])->toArray();
    echo json_encode(["runs"=>$runs,"queued_jobs"=>\\Illuminate\\Support\\Facades\\DB::table("jobs")->count(),
    "failed_jobs"=>\\Illuminate\\Support\\Facades\\DB::table("failed_jobs")->count()]);'''
  result=json.loads(execute(['php','-r',check],CMS,env))
  if len(result['runs'])!=1 or result['runs'][0]['status']!='succeeded' or result['runs'][0]['attempts']!=1 or result['queued_jobs'] or result['failed_jobs']:
   raise RuntimeError('Real database queue worker did not cleanly finish one real museum:export job: '+repr(result))
  output=stage/'published.json';manifest=stage/'snapshot-manifest.json'
  if not output.is_file() or not manifest.is_file():raise RuntimeError('Queue export has no isolated snapshot/manifest')
  contents=json.loads(output.read_text());signed=json.loads(manifest.read_text())
  digest=hashlib.sha256(output.read_bytes()).hexdigest()
  if digest!=signed['files']['published.json']['sha256'] or digest!=result['runs'][0]['sha256']:
   raise RuntimeError('Queued job status/digest diverges from PRIVATE source artifact')
  slugs=[x['slug'] for x in contents.get('entries',[])]
  if ENTRY not in slugs or 'qa-real-queue-draft-hidden' in slugs:
   raise RuntimeError('Queue exported unapproved draft or missed real queued article')
  if before!=hashlib.sha256((WEB/'src/data/published.json').read_bytes()).hexdigest():
   raise RuntimeError('Real DB queue modified the tracked Next public fixture instead of private stage')
  print('TRUE_LARAVEL_DATABASE_QUEUE_PASS '+json.dumps({'queued_runs':1,'actual_worker_processed':1,
    'private_snapshot_sha256':digest,'published_news_slug':ENTRY,'draft_excluded':True,
    'web_developer_fixture_unchanged':True},sort_keys=True),flush=True)
  # Isolated real Next build, never modifying the repository's src/data or out.
  target=workspace/'web-build'
  shutil.copytree(WEB,target,ignore=shutil.ignore_patterns('node_modules','.next','out','playwright-report','test-results'))
  (target/'node_modules').symlink_to(WEB/'node_modules',target_is_directory=True)
  # The real repository postbuild writes SEO aliases to ../../scripts from
  # the repository root; the isolated disposable QA build must NEVER edit
  # those production-facing files or require original site source HTML. Run
  # only Next's real production compiler for this queued-CMS content QA.
  package=target/'package.json'
  meta=json.loads(package.read_text(encoding='utf-8'))
  meta['scripts'].pop('postbuild',None)
  package.write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
  shutil.copy2(output,target/'src/data/published.json')
  shutil.copy2(manifest,target/'public/snapshot-manifest.json')
  # The normal CMS queue wrote MEDIA/DOCUMENTS to private stage too.
  for category in ('media','documents'):
   if (stage/category).exists():shutil.copytree(stage/category,target/'public'/category,dirs_exist_ok=True)
  built=execute(['npm','run','build','--','--webpack'],target,env,timeout=220)
  article=target/'out/news'/ENTRY/'index.html'
  if not article.is_file():raise RuntimeError('Next failed to create public page from REAL queued Laravel snapshot')
  page=article.read_text()
  if 'QA: Новость из настоящей очереди Laravel' not in page or 'qa-real-queue-draft-hidden' in page:
   raise RuntimeError('Next static HTML does not faithfully reflect approved real Laravel queue')
  if (target/'out/news/qa-real-queue-draft-hidden/index.html').exists():
   raise RuntimeError('Private CMS draft leaked to the public Next export')
  if 'noindex' not in page:raise RuntimeError('Pre-award queued Next site lost noindex protection')
  print('TRUE_LARAVEL_QUEUE_TO_REAL_NEXT_STATIC_PASS '+json.dumps({'html_relative':'news/'+ENTRY+'/index.html',
    'html_sha256':hashlib.sha256(article.read_bytes()).hexdigest(),'preview_noindex':True,'draft_static_route_absent':True},sort_keys=True),flush=True)
  # The already-tested courier can consume the actual *built* public content,
  # not the private CMS DB, queue journal or private source JSON.
  from verify_museum_two_contour_docker import test as network_acceptance
  report=network_acceptance(source_output=target/'out',required_news='news/'+ENTRY+'/index.html')
  if not report.get('queue_built_news_visible_by_HTTP'):
   raise RuntimeError('Real queued Laravel news never appeared through public Docker Nginx')
  print('TRUE_LARAVEL_WORKER_TO_ISOLATED_DOCKER_PUBLIC_HTTP_PASS',flush=True)

if __name__=='__main__':
 try:main()
 except Exception as e:
  print('QUEUE_E2E_ERROR '+str(e)[-1500:],file=sys.stderr)
  raise
