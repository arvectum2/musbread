#!/usr/bin/env python3
"""Isolated PHP-FPM HTTP/CGI load smoke, localhost ONLY, no museum production.

A purpose-built loopback-only HTTP bridge sends FastCGI requests to a private
PHP-FPM Unix socket. This measures real FPM workers and Laravel route handling;
the gateway is NOT nginx, HTTPS, or real production reverse proxy.
"""
from __future__ import annotations

import concurrent.futures
import json
import os
from pathlib import Path
import secrets
import socket
import struct
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import urllib.error
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
CMS=ROOT/'apps/cms'
ARCHIVE=ROOT/'.local_archive'
# FastCGI constants
BEGIN=1
END=3
PARAMS=4
STDIN=5
STDOUT=6
STDERR=7


def record(kind:int,content:bytes)->bytes:
    if len(content)>65535:
        raise ValueError('FastCGI record too long')
    pad=(-len(content))%8
    return struct.pack('!BBHHBB',1,kind,1,len(content),pad,0)+content+(b'\x00'*pad)


def length(number:int)->bytes:
    if number<128:
        return bytes([number])
    return struct.pack('!I',number|0x80000000)


def fcgi_request(sock_path:Path,params:dict[str,str])->tuple[int,dict[str,str],bytes]:
    stream=bytearray()
    for name,value in params.items():
        n=name.encode()
        v=value.encode()
        stream.extend(length(len(n))+length(len(v))+n+v)
    with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as sock:
        sock.settimeout(9)
        sock.connect(str(sock_path))
        sock.sendall(record(BEGIN,struct.pack('!HB5s',1,0,b'\0'*5))
                     +record(PARAMS,bytes(stream))+record(PARAMS,b'')
                     +record(STDIN,b''))
        response=bytearray()
        errors=bytearray()
        while True:
            head=b''
            while len(head)<8:
                chunk=sock.recv(8-len(head))
                if not chunk:
                    raise RuntimeError('FPM socket closed before response')
                head+=chunk
            version,kind,req_id,size,padding,_=struct.unpack('!BBHHBB',head)
            if version!=1 or req_id!=1:raise RuntimeError('Invalid FastCGI frame')
            body=b''
            while len(body)<size+padding:
                chunk=sock.recv(size+padding-len(body))
                if not chunk: raise RuntimeError('Truncated FastCGI response')
                body+=chunk
            data=body[:size]
            if kind==STDOUT:response.extend(data)
            if kind==STDERR:errors.extend(data)
            if kind==END:break
    if b'\r\n\r\n' not in response:
        raise RuntimeError('Invalid CGI response; '+errors.decode(errors='replace')[-300:])
    head,body=response.split(b'\r\n\r\n',1)
    headers={}
    status=200
    for raw in head.decode('latin-1').split('\r\n'):
        if ':' not in raw:continue
        name,value=raw.split(':',1)
        if name.lower()=='status':
            status=int(value.strip().split()[0])
        else:
            headers[name.strip()]=value.strip()
    return status,headers,bytes(body)


def main():
    ARCHIVE.mkdir(mode=0o700,exist_ok=True)
    suffix=secrets.token_hex(12)
    db=ARCHIVE/('fpm-load-'+suffix+'.sqlite')
    config=ARCHIVE/('fpm-load-'+suffix+'.conf')
    socket_path=ARCHIVE/('fpm-load-'+suffix+'.sock')
    pid=ARCHIVE/('fpm-load-'+suffix+'.pid')
    log=ARCHIVE/('fpm-load-'+suffix+'.log')
    env=os.environ.copy()
    env.update(DB_CONNECTION='sqlite',DB_DATABASE=str(db),DB_URL='',APP_ENV='local',
               SESSION_DRIVER='file',CACHE_STORE='file',QUEUE_CONNECTION='sync',
               APP_DEBUG='false')
    env['PHP_INI_SCAN_DIR']=env.get('PHP_INI_SCAN_DIR','')
    db.touch(mode=0o600)
    fpm=None
    http=None
    stop=False
    try:
        migrated=subprocess.run(['php','artisan','migrate','--force','--no-interaction'],
                                cwd=CMS,env=env,text=True,capture_output=True,timeout=70)
        if migrated.returncode:
            raise RuntimeError('Failed private SQLite migration: '+migrated.stderr[-500:])
        conf=f"""[global]
pid = {pid}
error_log = {log}
daemonize = no
[www]
listen = {socket_path}
listen.mode = 0600
pm = static
pm.max_children = 3
clear_env = no
catch_workers_output = yes
php_admin_value[memory_limit] = 128M
"""
        config.write_text(conf)
        config.chmod(0o600)
        fpm=subprocess.Popen(['php-fpm','--nodaemonize','--fpm-config',str(config)],
                             cwd=CMS,env=env,stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT)
        deadline=time.monotonic()+10
        while not socket_path.is_socket():
            if fpm.poll() is not None: raise RuntimeError('PHP-FPM exited during startup')
            if time.monotonic()>deadline: raise RuntimeError('PHP-FPM socket not ready')
            time.sleep(.05)
        # Only these three routes are eligible for GET, never other origins.
        allowed={'/up','/admin/login','/admin/museum-documents'}
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path not in allowed or self.client_address[0]!='127.0.0.1':
                    self.send_error(404)
                    return
                parameters={
                    'GATEWAY_INTERFACE':'CGI/1.1',
                    'REQUEST_METHOD':'GET',
                    'REQUEST_URI':self.path,
                    'SCRIPT_FILENAME':str(CMS/'public/index.php'),
                    'SCRIPT_NAME':'/index.php',
                    'DOCUMENT_ROOT':str(CMS/'public'),
                    'SERVER_SOFTWARE':'MusbreadLoopbackQA',
                    'SERVER_NAME':'127.0.0.1',
                    'SERVER_PORT':str(self.server.server_port),
                    'SERVER_PROTOCOL':'HTTP/1.1',
                    'HTTP_HOST':'127.0.0.1:'+str(self.server.server_port),
                    'REMOTE_ADDR':'127.0.0.1',
                    'CONTENT_LENGTH':'0',
                    'HTTP_ACCEPT':'text/html',
                    'HTTP_USER_AGENT':'MusbreadLocalFPMQA',
                }
                try:
                    status,headers,body=fcgi_request(socket_path,parameters)
                    self.send_response(status)
                    for name,value in headers.items():
                        if name.lower() not in ('connection','transfer-encoding','content-length'):
                            self.send_header(name,value)
                    self.send_header('Content-Length',str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                except Exception as error:
                    self.send_error(502,type(error).__name__)
            def log_message(self,*args):
                return
        http=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        listener=threading.Thread(target=http.serve_forever,daemon=True)
        listener.start()
        base='http://127.0.0.1:'+str(http.server_port)
        no_redirect=urllib.request.build_opener(
            type('RejectRedirect',(urllib.request.HTTPRedirectHandler,),{
                'redirect_request':lambda self,req,fp,code,msg,headers,url:None
            })()
        )
        def fetch(path):
            req=urllib.request.Request(base+path,headers={'User-Agent':'MusbreadLocalFPMQA'})
            start=time.perf_counter()
            try:
                with no_redirect.open(req,timeout=9) as response:
                    response.read(1024*1024)
                    status=response.status
            except urllib.error.HTTPError as e:
                status=e.code
                e.read(1000)
            return status,round((time.perf_counter()-start)*1000,2)
        warm=[fetch(path) for path in ('/up','/admin/login','/admin/museum-documents')]
        print('FPM_WARMUP',warm,flush=True)
        if warm[0][0]!=200 or warm[2][0] not in (302,303):
            raise RuntimeError('FPM warm-up failed '+str(warm))
        profiles=[]
        for parallel in (1,2,4,8):
            paths=['/up','/admin/museum-documents']*12
            started=time.perf_counter()
            with concurrent.futures.ThreadPoolExecutor(max_workers=parallel) as pool:
                responses=list(pool.map(fetch,paths))
            duration=round((time.perf_counter()-started)*1000,2)
            errors=[(path,result) for path,result in zip(paths,responses)
                    if result[0] != (200 if path=='/up' else 302)]
            if errors:raise RuntimeError('FPM HTTP response failures '+str(errors[:5]))
            latencies=sorted(result[1] for result in responses)
            item={'concurrency':parallel,'requests':len(responses),
                  'p95_ms':latencies[max(0,(len(latencies)*95+99)//100-1)],
                  'batch_ms':duration,'errors':0}
            profiles.append(item)
            print('FPM_HTTP',item,flush=True)
        data={'scope':'localhost HTTP bridge => PHP-FPM Unix socket => REAL Laravel routes',
              'not_nginx':True,'not_tls_or_production':True,'max_fpm_children':3,
              'database':'fresh private SQLite only','requests':sum(x['requests'] for x in profiles),
              'all_passed':True,'profiles':profiles}
        (ARCHIVE/'cms-local-fpm-http-load-20261020.json').write_text(
            json.dumps(data,ensure_ascii=False,indent=2)+'\n')
        print('FPM_HTTP_LOAD_PASS',data['requests'],flush=True)
    finally:
        if http is not None:
            http.shutdown()
            http.server_close()
        if fpm is not None:
            fpm.terminate()
            try:fpm.communicate(timeout=6)
            except subprocess.TimeoutExpired:
                fpm.kill()
                fpm.communicate(timeout=3)
        for path in (db,Path(str(db)+'-wal'),Path(str(db)+'-shm'),config,socket_path,pid):
            path.unlink(missing_ok=True)
        # Keep an error log only if failure evidence is useful.
        if log.exists() and not log.read_bytes().strip():
            log.unlink()


if __name__=='__main__':
    main()
