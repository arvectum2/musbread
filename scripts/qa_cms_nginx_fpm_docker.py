#!/usr/bin/env python3
"""Local, disposable Nginx→PHP-FPM→Laravel integrated HTTP test.

Only isolated Docker network and 127.0.0.1 published HTTP listener.
No access to existing museum servers, databases, or other Docker containers.
"""
from __future__ import annotations
import base64
import http.cookiejar
import re
import urllib.parse
import concurrent.futures
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import tempfile
import time
import urllib.error
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
ARCHIVE=ROOT/'.local_archive'
CMS=ROOT/'apps/cms'


def call(args,*,env=None,check=True,timeout=35):
    p=subprocess.run(args,cwd=CMS,env=env,capture_output=True,text=True,timeout=timeout)
    if check and p.returncode:
        raise RuntimeError('Container or CLI failed '+str(p.returncode)+': '+(p.stdout+p.stderr)[-1400:])
    return p


def bench():
    ARCHIVE.mkdir(exist_ok=True)
    suffix=secrets.token_hex(6)
    net='musbread-qa-net-'+suffix
    fpm='musbread-qa-fpm-'+suffix
    nginx='musbread-qa-nginx-'+suffix
    temp=ARCHIVE/('cms-nginx-fpm-'+suffix)
    storage=temp/'storage'
    db=storage/'qa.sqlite'
    config=temp/'nginx.conf'
    owned=[]
    network=False
    temp.mkdir(mode=0o700)
    storage.mkdir()
    for dir_name in ('framework/cache/data','framework/sessions','framework/views',
                     'framework/testing','logs','app/private'):
        (storage/dir_name).mkdir(parents=True,exist_ok=True)
    db.touch(mode=0o666)
    # Only a disposable volume. Docker's Apache/PHP FPM (www-data) needs rw.
    for item in [storage,*storage.rglob('*')]:
        if item.is_dir():item.chmod(0o777)
        else:item.chmod(0o666)

    key='base64:'+base64.b64encode(secrets.token_bytes(32)).decode()
    env=os.environ.copy()
    env.update(APP_ENV='local',APP_DEBUG='false',APP_KEY=key,
               DB_CONNECTION='sqlite',DB_DATABASE=str(db), DB_URL='',
               SESSION_DRIVER='file',CACHE_STORE='file',QUEUE_CONNECTION='sync',
               LOG_CHANNEL='stderr')
    # Test-only administrator: registered ONLY in the throwaway SQLite DB.
    qa_email='cms-qa-'+suffix+'@example.invalid'
    qa_password=secrets.token_urlsafe(22)
    env['MUSBREAD_QA_EMAIL']=qa_email
    env['MUSBREAD_QA_PASS']=qa_password
    qa_email_b='cms-qa-second-'+suffix+'@example.invalid'
    qa_password_b=secrets.token_urlsafe(22)
    env['MUSBREAD_QA_EMAIL_B']=qa_email_b
    env['MUSBREAD_QA_PASS_B']=qa_password_b
    # The CMS runs INSIDE container against a distinct mounted /app/storage DB.
    fpm_env=dict(APP_ENV='local',APP_DEBUG='false',APP_KEY=key,
                 DB_CONNECTION='sqlite',DB_DATABASE='/app/storage/qa.sqlite',DB_URL='',
                 SESSION_DRIVER='file',CACHE_STORE='file',QUEUE_CONNECTION='sync',
                 LOG_CHANNEL='stderr')
    config.write_text('''server {
    listen 8080;
    server_name _;
    root /app/public;
    index index.php;
    access_log off;
    add_header X-Musbread-Isolated-QA "1" always;
    location ~ /\\. { deny all; }
    location / {
        try_files $uri $uri/ /index.php?$query_string;
    }
    location ~ \\.php$ {
        include fastcgi_params;
        fastcgi_pass fpm:9000;
        fastcgi_param SCRIPT_FILENAME /app/public/index.php;
        fastcgi_param SCRIPT_NAME /index.php;
        fastcgi_param HTTP_HOST $http_host;
        fastcgi_read_timeout 15s;
    }
}
''')
    config.chmod(0o600)
    try:
        migrated=call(['php','artisan','migrate','--force','--no-interaction'],env=env,timeout=70)
        print('NGINX_FPM_PRIVATE_MIGRATION_PASS',len(migrated.stdout.splitlines()),flush=True)
        # Do not interpolate credentials in command-line args; tinker reads
        # them from this test process's environment and only the QA database.
        seed=r'''
        $db = realpath((string) env("DB_DATABASE"));
        $prefix = realpath(base_path("../../.local_archive"));
        if ($db === false || $prefix === false || !str_starts_with($db, $prefix."/cms-nginx-fpm-")
            || basename($db) !== "qa.sqlite" || env("APP_ENV") !== "local") {
            throw new RuntimeException("Refusing non-test database");
        }
        \\MoonShine\\Laravel\\Models\\MoonshineUser::create([
            "name"=>"QA Administrator",
            "email"=>env("MUSBREAD_QA_EMAIL"),
            "password"=>\\Illuminate\\Support\\Facades\\Hash::make(env("MUSBREAD_QA_PASS")),
            "moonshine_user_role_id"=>1
        ]);
        \\MoonShine\\Laravel\\Models\\MoonshineUser::create([
            "name"=>"QA Second Editor", "email"=>env("MUSBREAD_QA_EMAIL_B"),
            "password"=>\\Illuminate\\Support\\Facades\\Hash::make(env("MUSBREAD_QA_PASS_B")),
            "moonshine_user_role_id"=>1
        ]);
        $entry = \\App\\Models\\MuseumEntry::create([
            "type"=>"news", "slug"=>"synthetic-conflict-test",
            "title"=>"Synthetic editor conflict",
            "body"=>"<p>Original synthetic material</p>",
            "status"=>"draft"
        ]);
        echo "QA_ENTRY_ID=".$entry->id."\\n";
        '''.replace('\\\\','\\')
        seeded=call(['php','artisan','tinker','--execute',seed],env=env,timeout=20)
        match=re.search(r'QA_ENTRY_ID=(\d+)', seeded.stdout)
        if not match:raise RuntimeError('Did not create isolated synthetic entry')
        conflict_entry_id=int(match.group(1))
        call(['docker','network','create',net],timeout=15)
        network=True
        argv=['docker','run','-d','--rm','--name',fpm,'--network',net,
              '--network-alias','fpm','--memory=400m','--cpus=2.0',
              '--mount',f'type=bind,source={CMS},target=/app,readonly',
              '--mount',f'type=bind,source={storage},target=/app/storage',
              '--workdir','/app']
        for name,value in fpm_env.items():
            argv+=['-e',name+'='+value]
        argv+=['php:8.4-fpm-alpine']
        call(argv,timeout=20)
        owned.append(fpm)
        call(['docker','run','-d','--rm','--name',nginx,'--network',net,
              '--memory=128m','--cpus=1.0',
              '--publish','127.0.0.1::8080',
              '--mount',f'type=bind,source={CMS / "public"},target=/app/public,readonly',
              '--mount',f'type=bind,source={config},target=/etc/nginx/conf.d/default.conf,readonly',
              'nginx:stable-alpine'],timeout=20)
        owned.append(nginx)
        port_spec=call(['docker','port',nginx,'8080/tcp']).stdout.strip()
        if not port_spec.startswith('127.0.0.1:'):
            raise RuntimeError('HTTP port is not loopback only: '+port_spec)
        endpoint='http://'+port_spec

        opener=urllib.request.build_opener(type('NeverFollow',(
            urllib.request.HTTPRedirectHandler,),{
            'redirect_request':lambda self,req,fp,code,msg,headers,url:None})())
        def get(path, authenticated=False):
            start=time.monotonic()
            headers={'User-Agent':'MusbreadIsolatedNginxFPMQA'}
            if authenticated:
                headers['Cookie']=cookie_header
            request=urllib.request.Request(endpoint+path,headers=headers)
            try:
                with opener.open(request,timeout=12) as response:
                    status=response.status
                    headers=dict(response.headers)
                    body=response.read(2_000_000)
            except urllib.error.HTTPError as error:
                status=error.code
                headers=dict(error.headers)
                body=error.read(2000)
            return {'status':status,'latency_ms':round((time.monotonic()-start)*1000,2),
                    'qa_header':headers.get('X-Musbread-Isolated-QA'),
                    'redirect_to':headers.get('Location',''),
                    'body_size':len(body)}

        deadline=time.monotonic()+22
        while True:
            try:
                warm={path:get(path) for path in ('/up','/admin/login','/admin/museum-documents')}
                if warm['/up']['status']==200 and warm['/admin/login']['status']==200 and (
                    warm['/admin/museum-documents']['status'] in (302,303)):
                    break
            except (OSError,TimeoutError,urllib.error.URLError):
                pass
            if time.monotonic()>deadline:
                logs=call(['docker','logs','--tail','25',fpm],check=False).stderr
                errors=call(['docker','logs','--tail','25',nginx],check=False).stderr
                raise RuntimeError('Nginx/FPM warm-up mismatch: '+str(locals().get('warm'))+
                                   ' FPM='+logs[-1200:]+' NGINX='+errors[-750:])
            time.sleep(.35)
        print('NGINX_FPM_WARMUP',warm,flush=True)
        private=get('/storage/museum/media/secret.webp')
        if private['status']!=404:raise RuntimeError('Private original unexpectedly served')
        hidden=get('/.env')
        if hidden['status'] not in (403,404):raise RuntimeError('Secret file exposed')
        print('NGINX_FPM_PRIVATE_ACCESS',private['status'],hidden['status'],flush=True)
        # Genuine session-cookie login via Nginx/FPM, with the hidden _token
        # received from GET /admin/login; no simulated actor or direct guard.
        jar=http.cookiejar.CookieJar()
        browser=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar),
            type('NoFollow', (urllib.request.HTTPRedirectHandler,), {
            'redirect_request':lambda self,req,fp,code,msg,headers,url:None})())
        with browser.open(endpoint+'/admin/login',timeout=10) as login_page:
            login_html=login_page.read(300000).decode('utf-8','replace')
        tokens=re.findall(r'name="_token"[^>]*value="([^"]+)"',login_html)
        if not tokens:
            tokens=re.findall(r'value="([^"]+)"[^>]*name="_token"',login_html)
        if not tokens:
            raise RuntimeError('Live MoonShine login form lacks expected CSRF hidden input')
        auth_body=urllib.parse.urlencode({
            'username':qa_email,'password':qa_password,'_token':tokens[0]}).encode()
        request=urllib.request.Request(endpoint+'/admin/authenticate',data=auth_body,method='POST',
            headers={'Content-Type':'application/x-www-form-urlencoded',
                     'Origin':endpoint,'Referer':endpoint+'/admin/login'})
        try:
            with browser.open(request,timeout=10) as login_response:
                login_status=login_response.status
        except urllib.error.HTTPError as e:
            login_status=e.code
            login_location=e.headers.get('Location','')
        print('NGINX_FPM_AUTH_DEBUG', {'login_status':login_status,
             'location':locals().get('login_location',''),
             'cookies':[c.name for c in jar]},flush=True)
        try:
            with browser.open(endpoint+'/admin/museum-documents',timeout=10) as private_page:
                auth_status=private_page.status
                authenticated_body=private_page.read(300000)
        except urllib.error.HTTPError as e:
            auth_status=e.code
            print('NGINX_FPM_AUTH_REDIRECT',auth_status,e.headers.get('Location',''),flush=True)
            raise RuntimeError('Synthetic login did not grant admin session')
        if login_status not in (302,303) or auth_status!=200:
            raise RuntimeError('Real session login/access invalid: '
                               +str((login_status,auth_status)))
        print('NGINX_FPM_AUTHENTICATED_ADMIN_PASS',
              {'login_status':login_status,'documents_status':auth_status,
               'session_cookie_count':len(jar)},flush=True)
        # Two actual, independent MoonShine browser sessions with different
        # synthetic accounts now submit the SAME entry. The second uses a
        # stale fingerprint, so the real Nginx HTTP response must be a usable
        # conflict-comparison page, not MoonShine's generic 500 toast.
        jar_b=http.cookiejar.CookieJar()
        browser_b=urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(jar_b),
            type('NoFollow', (urllib.request.HTTPRedirectHandler,), {
                'redirect_request':lambda self,req,fp,code,msg,headers,url:None})())
        def browser_page(client,path):
            with client.open(endpoint+path,timeout=12) as response:
                return response.read(300000).decode('utf-8','replace')
        login_html_b=browser_page(browser_b,'/admin/login')
        token_b=re.search(r'name="_token"[^>]*value="([^"]+)"',login_html_b)
        if not token_b:raise RuntimeError('Second editor CSRF field missing')
        credentials_b=urllib.parse.urlencode({
            'username':qa_email_b,'password':qa_password_b,
            '_token':token_b.group(1)}).encode()
        login_request_b=urllib.request.Request(endpoint+'/admin/authenticate',
            data=credentials_b,method='POST',headers={
                'Content-Type':'application/x-www-form-urlencoded',
                'Origin':endpoint,'Referer':endpoint+'/admin/login'})
        try:
            browser_b.open(login_request_b,timeout=10)
        except urllib.error.HTTPError as error:
            if error.code!=302:raise
        form_url='/admin/resource/museum-entry-resource/museum-entry-form-page/'+str(conflict_entry_id)
        form_a=browser_page(browser,form_url)
        form_b=browser_page(browser_b,form_url)
        # Real authenticated editor navigation; the query context must
        # select the current entry in BOTH attachment libraries.
        scoped_media='/admin/museum-media?entry='+str(conflict_entry_id)
        scoped_docs='/admin/museum-documents?entry='+str(conflict_entry_id)
        if not all(path in form_a for path in (
            scoped_media,scoped_docs,
            '/admin/museum-entries/'+str(conflict_entry_id)+'/preview',
            '/admin/museum-content/preflight#entry-'+str(conflict_entry_id)
        )):
            raise RuntimeError('Live editor form is missing contextual workflow links')
        for path in (scoped_media, scoped_docs):
            scoped_html=browser_page(browser,path)
            if ('Текущий материал:' not in scoped_html or
                'Synthetic editor conflict' not in scoped_html or
                not re.search(r'<option[^>]*value="'+str(conflict_entry_id)
                              +r'"[^>]*selected', scoped_html)):
                raise RuntimeError('Live media/document library lost selected entry: '+path)
        print('NGINX_FPM_EDITOR_WORKFLOW_NAVIGATION_PASS',
              {'links':4,'scoped_libraries':2,'preselected_entry':True},flush=True)
        def form_field(html,key):
            pattern=r'<input[^>]*name="'+re.escape(key)+r'"[^>]*>'
            target=re.search(pattern,html)
            if not target:raise RuntimeError('MoonShine form missing '+key)
            value=re.search(r'value="([^"]*)"',target.group(0))
            if not value:raise RuntimeError('MoonShine form missing value '+key)
            return value.group(1)
        revision_a=form_field(form_a,'_museum_revision_sha256')
        revision_b=form_field(form_b,'_museum_revision_sha256')
        if revision_a!=revision_b:raise RuntimeError('Two editors opened different versions')
        if 'data-async' in form_a.split('form-resource-museum-entry-resource',1)[-1].split('</form>',1)[0]:
            raise RuntimeError('Conflict editor form is unexpectedly AJAX-only')
        def submit(client,html,body):
            values={
                '_token':form_field(html,'_token'),'_method':'PUT',
                '_museum_revision_sha256':form_field(html,'_museum_revision_sha256'),
                'slug':'synthetic-conflict-test','title':'Synthetic editor conflict',
                'type':'news','status':'draft','body':body,
            }
            request=urllib.request.Request(
                endpoint+'/admin/resource/museum-entry-resource/crud/'+str(conflict_entry_id),
                data=urllib.parse.urlencode(values).encode(),method='POST',
                headers={'Content-Type':'application/x-www-form-urlencoded',
                         'Origin':endpoint,'Referer':endpoint+form_url})
            try:
                with client.open(request,timeout=12) as response:
                    return response.status,response.read(300000).decode('utf-8','replace'),dict(response.headers)
            except urllib.error.HTTPError as e:
                return e.code,e.read(300000).decode('utf-8','replace'),dict(e.headers)
        first_status,first_body,_=submit(browser,form_a,"<p>Editor saved a newer version</p>")
        if first_status not in (302,303):
            raise RuntimeError('First editor did not save via HTTP: '+str(first_status))
        second_status,comparison,comparison_headers=submit(
            browser_b,form_b,'<p>My stale UNSAVED editor draft & special symbols</p>')
        if second_status!=409 or not all(fragment in comparison for fragment in (
            'Другой редактор изменил материал','Мой несохранённый вариант',
            'saved a newer version','UNSAVED editor draft','museum-editor-conflict.js'
        )):
            raise RuntimeError('Live conflict response failed '+str(second_status)+' '+comparison[-420:])
        if '<p>My stale UNSAVED' in comparison or 'no-store' not in comparison_headers.get('Cache-Control',''):
            raise RuntimeError('Unsaved HTML not escaped or private no-store missing')
        if 'javascript' in comparison_headers.get('Content-Type','').lower():
            raise RuntimeError('Unexpected MIME for conflict response')
        with browser_b.open(endpoint+'/js/museum-editor-conflict.js',timeout=8) as js_resp:
            if js_resp.status!=200 or b'museum-unsaved-draft.json' not in js_resp.read():
                raise RuntimeError('Local conflict download UX script inaccessible')
        latest_form=browser_page(browser_b,form_url)
        if 'saved a newer version' not in latest_form:
            raise RuntimeError('Current saved source differs from winner')
        print('NGINX_FPM_TWO_EDITOR_CONFLICT_HTTP_PASS',
            {'different_session_cookies':sorted(c.value for c in jar)!=sorted(c.value for c in jar_b),
             'first_save_status':first_status,'second_save_status':second_status,
             'draft_preserved_escaped':True,'latest_form_unchanged_by_stale_submit':True},
            flush=True)
        # Hold only temporary localhost cookies; never write cookie values
        # to the report or another file.
        cookie_header='; '.join(c.name+'='+c.value for c in jar)
        profiles=[]
        for parallel in (1,2,4,8):
            requests=[('/up',False),('/admin/museum-documents',False),
                      ('/admin/museum-documents',True)]*8
            start=time.monotonic()
            with concurrent.futures.ThreadPoolExecutor(max_workers=parallel) as executor:
                results=list(executor.map(lambda req:get(*req),requests))
            errors=[(p,r) for p,r in zip(requests,results)
                    if r['status']!=(200 if p[0]=='/up' or p[1] else 302)
                    or r['qa_header']!='1']
            if errors:
                raise RuntimeError('Nginx-FPM wrong status '+str(errors[:3]))
            lat=sorted(r['latency_ms'] for r in results)
            record={'concurrency':parallel,'requests':24,'errors':0,
                    'p95_ms':lat[(24*95+99)//100-1],
                    'total_wall_ms':round((time.monotonic()-start)*1000,2)}
            profiles.append(record)
            print('NGINX_FPM_HTTP',record,flush=True)
        result={
            'scope':'Docker Nginx -> Docker PHP 8.4 FPM -> actual Laravel; localhost only',
            'docker_network_dedicated':True,'docker_egress_disabled':False,'exposed_host_interface':'127.0.0.1',
            'test_database':'disposable SQLite, not museum',
            'production_access':False,
            'auth_cookie_login_tested':True,
            'authenticated_admin_documents_status':auth_status,
            'login_post_status':login_status,
            'real_museum_pdf_download_tested':False,
            'nginx_fpm_routes_tested':['/up','/admin/login','/admin/authenticate',
                                       '/admin/museum-documents (guest and authenticated)',
                                       '/storage/museum/media/secret.webp','/.env'],
            'editorial_workflow_navigation_tested':True,
            'scoped_editor_libraries_tested':['/admin/museum-media?entry',
                                             '/admin/museum-documents?entry'],
            'two_editor_conflict_real_http_tested':True,
            'two_editor_stale_submit_status':second_status,
            'two_editor_first_save_status':first_status,
            'unsaved_draft_preserved_in_escaped_409_html':True,
            'authenticated_parallel_requests':32,
            'anonymous_private_route_requests':32,
            'https_tested':False,
            'total_parallel_load_requests':96,'no_unexpected_statuses':True,
            'profiles':profiles,
        }
        (ARCHIVE/'cms-real-nginx-fpm-http-20261020.json').write_text(
            json.dumps(result,ensure_ascii=False,indent=2)+'\n')
        print('NGINX_FPM_HTTP_PASS',96,flush=True)
    finally:
        for name in reversed(owned):
            state=call(['docker','inspect',name,'--format',
                '{{json .NetworkSettings.Ports}}'],check=False,timeout=8)
            logs=call(['docker','logs','--tail','12',name],check=False,timeout=8)
            if not (ARCHIVE/'cms-real-nginx-fpm-http-20261020.json').exists():
                print('NGINX_FPM_DIAGNOSTIC',name,'PORTS',state.stdout[-350:],
                      'LOGS', (logs.stdout+logs.stderr)[-1200:],flush=True)
            call(['docker','rm','-f',name],check=False,timeout=15)
        if network:call(['docker','network','rm',net],check=False,timeout=15)
        shutil.rmtree(temp,ignore_errors=True)


if __name__=='__main__':
    bench()
