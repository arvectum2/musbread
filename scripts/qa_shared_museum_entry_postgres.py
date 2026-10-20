#!/usr/bin/env python3
"""Use a BRAND NEW disposable, loopback-only Docker PostgreSQL for CMS race QA.

Never exec into any preexisting container or run migrations on another DB.
Both independent host PHP processes connect to the same temporary Postgres.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import time

ROOT=Path(__file__).resolve().parents[1]
ARCHIVE=ROOT/'.local_archive'
CMS=ROOT/'apps/cms'
WORKER=ROOT/'scripts/qa_shared_museum_entry_pg_worker.php'


def sh(command,*,env=None,timeout=40,check=True):
    p=subprocess.run(command,cwd=CMS,env=env,text=True,capture_output=True,timeout=timeout)
    if check and p.returncode:
        raise RuntimeError('Command failed '+str(p.returncode)+': '+(p.stdout+p.stderr)[-800:])
    return p


def main():
    ARCHIVE.mkdir(exist_ok=True)
    suffix=secrets.token_hex(6)
    name='musbread-qa-pg-'+suffix
    db_user='musbread_qa_'+suffix
    db_password=secrets.token_urlsafe(28)
    # published to 127.0.0.1 only: never exposes PostgreSQL to LAN.
    container=None
    ready=[]
    go=None
    env=os.environ.copy()
    try:
        sh(['docker','run','-d','--rm','--name',name,
            '-e','POSTGRES_USER='+db_user,
            '-e','POSTGRES_PASSWORD='+db_password,
            '-e','POSTGRES_DB='+db_user,
            '-p','127.0.0.1::5432',
            '--memory=400m','--cpus=2',
            '--tmpfs','/var/lib/postgresql/data:rw,noexec,nosuid,size=192m',
            'pgvector/pgvector:pg16'],timeout=35)
        container=name
        port_result=sh(['docker','port',name,'5432/tcp']).stdout.strip()
        if not port_result.startswith('127.0.0.1:'):
            raise RuntimeError('Postgres is not bound strictly to loopback: '+port_result)
        port=port_result.rsplit(':',1)[1]
        env.update(DB_CONNECTION='pgsql',DB_HOST='127.0.0.1',DB_PORT=port,
                   DB_DATABASE=db_user,DB_USERNAME=db_user,DB_PASSWORD=db_password,
                   DB_URL='', MUSBREAD_QA_EXPLICIT='1',APP_ENV='local',
                   CACHE_STORE='array',QUEUE_CONNECTION='sync',
                   SESSION_DRIVER='array',DB_SSLMODE='prefer')
        deadline=time.monotonic()+24
        while True:
            p=sh(['docker','exec',name,'pg_isready','-U',db_user,'-d',db_user],timeout=6,check=False)
            if p.returncode==0:break
            if time.monotonic()>deadline:
                raise RuntimeError('Disposable Postgres did not become ready')
            time.sleep(.3)
        migrated=sh(['php','artisan','migrate','--force','--no-interaction'],env=env,timeout=75)
        print('POSTGRES_MIGRATIONS_PASS',len(migrated.stdout.splitlines()),flush=True)
        fresh=sh(['php',str(WORKER),'init'],env=env)
        entry=json.loads(fresh.stdout)
        outcomes=[]
        for run in range(1,9):
            before=json.loads(sh(['php',str(WORKER),'read',str(entry['id'])],env=env).stdout)
            ready=[ARCHIVE/('pg-ready-'+secrets.token_hex(12)) for _ in range(2)]
            go=ARCHIVE/('pg-go-'+secrets.token_hex(12))
            children=[]
            try:
                for who,barrier in zip(('A','B'),ready):
                    children.append(subprocess.Popen(
                        ['php',str(WORKER),'save',str(entry['id']),before['revision'],
                         who,str(barrier),str(go)],
                        cwd=CMS,env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE))
                deadline=time.monotonic()+12
                while not all(path.is_file() for path in ready):
                    if time.monotonic()>deadline or any(p.poll() is not None for p in children):
                        raise RuntimeError('Postgres race did not reach dual process barrier')
                    time.sleep(.02)
                go.write_text('GO')
                results=[]
                for p in children:
                    stdout,stderr=p.communicate(timeout=18)
                    results.append((p.returncode,stdout.strip(),stderr.strip()))
                if sorted(x[0] for x in results)!=[0,9]:
                    raise RuntimeError('Must have exactly one winner: '+str(results))
                winner='A' if results[0][0]==0 else 'B'
                after=json.loads(sh(['php',str(WORKER),'read',str(entry['id'])],env=env).stdout)
                if after['body']!='<p>Editor '+winner+' saved</p>' or after['revision']==before['revision']:
                    raise RuntimeError('Lost/update mismatch '+str(results))
                outcomes.append({'round':run,'winner':winner,
                                 'loser_result':results[1 if winner=='A' else 0][1]})
                print('POSTGRES_RACE',run,'WINNER',winner,'OTHER',
                      outcomes[-1]['loser_result'],flush=True)
            finally:
                for p in children:
                    if p.poll() is None:p.kill()
                    p.communicate()
                for f in ready+[go]:f.unlink(missing_ok=True)
        details={
            'test':'Postgres 16 Docker isolated, shared DB, independent PHP processes',
            'rounds':outcomes,'exactly_one_success_each_round':True,
            'lost_updates':0,'loopback_only':True,
            'production_server_or_data_touched':False,
            'migrations': 'PASS',
        }
        (ARCHIVE/'cms-postgres-shared-editor-race-20261020.json').write_text(
            json.dumps(details,ensure_ascii=False,indent=2)+'\n')
        print('POSTGRES_SHARED_EDITOR_RACE_PASS',len(outcomes),flush=True)
    finally:
        if container is not None:
            sh(['docker','rm','-f',container],timeout=20,check=False)
        for file in ready+([go] if go else []):
            file.unlink(missing_ok=True)


if __name__=='__main__':
    main()
