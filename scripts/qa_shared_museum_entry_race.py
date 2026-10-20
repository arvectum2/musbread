#!/usr/bin/env python3
"""Actual two-process race in ONE disposable SQLite DB: fail closed, no lost update.

Uses the same MuseumEntryRevisionGuard called by MoonShine beforeUpdating and
a transaction held through model save. This exercises shared file-backed DB
concurrency, unlike isolated PHPUnit :memory: workers. Not a real network
HTTP test, nor a PostgreSQL/MySQL row-lock proof.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
import secrets
import subprocess
import time

ROOT=Path(__file__).resolve().parents[1]
ARCHIVE=ROOT/'.local_archive'
CMS=ROOT/'apps/cms'
WORKER=ROOT/'scripts/qa_shared_museum_entry_worker.php'


def invoke(args, env, timeout=30):
    result=subprocess.run(args, cwd=CMS,env=env,text=True,capture_output=True,timeout=timeout)
    if result.returncode: raise RuntimeError(
        'worker failed: '+str(result.returncode)+': '+(result.stdout+result.stderr)[-900:])
    return result.stdout.strip()


def main():
    ARCHIVE.mkdir(exist_ok=True)
    suffix=secrets.token_hex(12)
    db=ARCHIVE/('sqlite-race-'+suffix+'.sqlite')
    env=os.environ.copy()
    env.update(DB_CONNECTION='sqlite',DB_DATABASE=str(db), DB_URL='', APP_ENV='local',
               SESSION_DRIVER='array', CACHE_STORE='array',QUEUE_CONNECTION='sync')
    outcomes=[]
    try:
        db.touch(mode=0o600)
        print('SHARED_DB_MIGRATE',flush=True)
        invoke(['php','artisan','migrate','--force','--no-interaction'],env,timeout=75)
        fixture=json.loads(invoke(['php',str(WORKER),'init'],env))
        entry_id=str(fixture['id'])
        for round_number in (1,2,3):
            before=json.loads(invoke(['php',str(WORKER),'read',entry_id],env))
            ready=[ARCHIVE/('shared-ready-'+secrets.token_hex(12)) for _ in (0,1)]
            go=ARCHIVE/('shared-go-'+secrets.token_hex(12))
            children=[]
            try:
                for actor,path in zip(('A','B'), ready):
                    children.append(subprocess.Popen([
                        'php',str(WORKER),'save',entry_id,before['revision'],actor,
                        str(path),str(go)],cwd=CMS,env=env,
                        text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE))
                deadline=time.monotonic()+14
                while not all(path.is_file() for path in ready):
                    if time.monotonic()>deadline:
                        raise RuntimeError('Two PHP transactions did not reach shared DB barrier')
                    if any(c.poll() is not None for c in children):
                        raise RuntimeError('A worker failed before race barrier')
                    time.sleep(.02)
                go.write_text('GO\n')
                results=[]
                for child in children:
                    out,err=child.communicate(timeout=20)
                    results.append((child.returncode,out.strip(),err.strip()))
                statuses=[r[0] for r in results]
                if sorted(statuses)!=[0,9]:
                    raise RuntimeError('Lost-update race outcome must be one writer and one conflict: '+str(results))
                after=json.loads(invoke(['php',str(WORKER),'read',entry_id],env))
                winner='A' if results[0][0]==0 else 'B'
                if after['body'] != '<p>Редактор '+winner+' сохранил обновление</p>':
                    raise RuntimeError('Stored DB entry does not match sole winning editor')
                if after['revision']==before['revision']:
                    raise RuntimeError('Post-update revision did not change')
                outcomes.append(dict(round=round_number,winner=winner,
                    conflict=results[1 if winner=='A' else 0][1],
                    shared_sqlite_file=True,stored_body_matches_winner=True))
                print('SHARED_DB_RACE',round_number,'WINNER',winner,
                    'CONFLICT',outcomes[-1]['conflict'],flush=True)
            finally:
                for c in children:
                    if c.poll() is None:
                        c.kill()
                    c.communicate()
                for path in ready+[go]:path.unlink(missing_ok=True)
        record=dict(test='two independent PHP processes editing one CMS entry',
                    database='ONE synthetic file-backed SQLite, NOT museum database',
                    rounds=outcomes,one_winner_per_round=True,no_lost_updates=True,
                    no_production_or_network_access=True)
        (ARCHIVE/'cms-shared-sqlite-editor-race-20261020.json').write_text(
            json.dumps(record,ensure_ascii=False,indent=2)+'\n')
        print('SHARED_SQLITE_EDITOR_RACE_PASS',len(outcomes),flush=True)
    finally:
        for ending in ('','-shm','-wal','-journal'):
            Path(str(db)+ending).unlink(missing_ok=True)


if __name__=='__main__':
    main()
