#!/usr/bin/env python3
"""Docker-independent real CMS HTTP + Playwright test, localhost only.

Boots an isolated Laravel PHP development server with an isolated storage
directory and a throwaway file-backed SQLite DB. It never reads the configured
CMS database or contacts a public museum site.
"""
from __future__ import annotations
import base64
import os
from pathlib import Path
import secrets
import shutil
import socket
import subprocess
import time
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
CMS=ROOT/'apps/cms'
ARCHIVE=ROOT/'.local_archive'


def run(args,env,timeout=45):
    p=subprocess.run(args,cwd=CMS,env=env,text=True,capture_output=True,timeout=timeout)
    if p.returncode:
        raise RuntimeError('Isolated Laravel command failed: '+(p.stdout+p.stderr)[-1000:])
    return p.stdout


def main():
    ARCHIVE.mkdir(mode=0o700,exist_ok=True)
    suffix=secrets.token_hex(10)
    root=ARCHIVE/('cms-local-ux-'+suffix)
    storage=root/'storage'
    db=storage/'qa.sqlite'
    router=root/'router.php'
    root.mkdir(mode=0o700)
    for path in ['app','framework/cache/data','framework/sessions',
                 'framework/views','framework/testing','logs']:
        (storage/path).mkdir(parents=True,exist_ok=True)
    db.touch(mode=0o600)
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0))
        port=sock.getsockname()[1]
    endpoint='http://127.0.0.1:'+str(port)
    key='base64:'+base64.b64encode(secrets.token_bytes(32)).decode('ascii')
    email='cms-local-ux-'+suffix+'@example.invalid'
    password=secrets.token_urlsafe(22)
    env=os.environ.copy()
    env.update(APP_ENV='local',APP_DEBUG='false',APP_KEY=key, APP_URL=endpoint,
               LARAVEL_STORAGE_PATH=str(storage), DB_CONNECTION='sqlite',
               DB_DATABASE=str(db),DB_URL='',SESSION_DRIVER='file',
               CACHE_STORE='file',QUEUE_CONNECTION='sync',
               MUSBREAD_QA_EMAIL=email,MUSBREAD_QA_PASS=password,
               MUSBREAD_QA_BASE_URL=endpoint,
               MUSBREAD_QA_ENFORCE=os.getenv('MUSBREAD_QA_ENFORCE','1'))
    server=None
    try:
        # Never migrate the CMS live database. DB name & application storage
        # are both uniquely generated from the test storage root.
        migrations=run(['php','artisan','migrate','--force','--no-interaction'],env,timeout=75)
        print('LOCAL_UX_MIGRATIONS_PASS',len(migrations.splitlines()),flush=True)
        seed=r'''
        $db=realpath((string) env("DB_DATABASE"));
        $storage=realpath(storage_path());
        if ($db===false || $storage===false
            || dirname($db)!==$storage
            || basename($db)!=="qa.sqlite"
            || !str_contains($db,"/cms-local-ux-")
            || env("APP_ENV")!=="local") {
          throw new RuntimeException("Refusing non-synthetic CMS database");
        }
        \MoonShine\Laravel\Models\MoonshineUser::create([
          "name"=>"Editor Mobile QA",
          "email"=>env("MUSBREAD_QA_EMAIL"),
          "password"=>\Illuminate\Support\Facades\Hash::make(env("MUSBREAD_QA_PASS")),
          "moonshine_user_role_id"=>1
        ]);
        $entry=\App\Models\MuseumEntry::create([
          "type"=>"news", "slug"=>"ux-synthetic-local",
          "title"=>"Synthetic editorial UX",
          "body"=>"<p>Only fake data in this test material.</p>",
          "status"=>"draft"
        ]);
        $run=\App\Models\MuseumPublicationRun::create([
            "status"=>"failed", "attempts"=>1, "error_type"=>"RuntimeException",
            "started_at"=>now()->subMinute(), "finished_at"=>now()
        ]);
        \App\Models\MuseumContentApproval::create([
            "museum_entry_id"=>$entry->id, "actor_id"=>1,
            "revision_sha256"=>\App\Support\MuseumApprovalRevision::fingerprint($entry->fresh()),
            "approved_at"=>now("UTC"), "dispatch_status"=>"queued",
            "publication_run_id"=>$run->id
        ]);
        echo "QA_ENTRY_ID=".$entry->id."\n";
        '''
        created=run(['php','artisan','tinker','--execute',seed],env,timeout=25)
        import re
        match=re.search(r'QA_ENTRY_ID=(\d+)',created)
        if not match:raise RuntimeError('Cannot seed isolated entry')
        env['MUSBREAD_QA_ENTRY']=match.group(1)
        # A temporary Laravel router: static public files are handled by PHP
        # dev server; all nonfile requests use the standard public/index.php.
        pub=str(CMS/'public')
        router.write_text('<?php\n'
            '$path=parse_url($_SERVER["REQUEST_URI"],PHP_URL_PATH);\n'
            '$public='+repr(pub).replace("'",'"')+';\n'
            'if ($path!=="/" && is_file($public.$path))return false;\n'
            'require $public."/index.php";\n')
        server=subprocess.Popen(['php','-S','127.0.0.1:'+str(port),
                                 '-t',str(CMS/'public'),str(router)],
                                env=env,cwd=CMS,stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL)
        deadline=time.monotonic()+16
        while True:
            if server.poll() is not None:raise RuntimeError('Isolated PHP server exited')
            try:
                with urllib.request.urlopen(endpoint+'/up',timeout=2) as response:
                    if response.status==200:break
            except Exception:pass
            if time.monotonic()>deadline:
                raise RuntimeError('Isolated PHP server did not become ready')
            time.sleep(.15)
        print('LOCAL_UX_HTTP_READY',flush=True)
        out=run(['node',str(ROOT/'scripts/qa_cms_editorial_browser_audit.mjs')],
                env,timeout=115)
        print(out[-5500:],flush=True)
        print('LOCAL_UX_BROWSER_PASS',flush=True)
    finally:
        if server is not None:
            server.terminate()
            try:server.wait(timeout=4)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait(timeout=3)
        shutil.rmtree(root,ignore_errors=True)


if __name__=='__main__':
    main()
