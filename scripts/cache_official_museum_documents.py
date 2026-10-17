#!/usr/bin/env python3
"""Manual, resumable, source-verified private archive of museum public PDFs/DOCXs.

Copies original bytes only (never rewrites legal documents). No CMS publication.
Obeys official robots.txt Crawl-delay 10; retains the existing SHA256 manifest.
"""
from __future__ import annotations
import argparse
from datetime import datetime,timezone
from hashlib import sha256
import json
from pathlib import Path
import subprocess
from time import sleep
from urllib.parse import urlparse
from urllib.request import Request,urlopen

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'apps/web/src/data/official-page-snapshots.json'
ARCHIVE=ROOT/'.local_archive/official-site-originals'
HOST='https://muzei-xleb.ru'

def save(path: Path, docs: dict, errors: dict) -> None:
    payload={'source':HOST,'generated_utc':datetime.now(timezone.utc).isoformat(timespec='seconds'),
             'files':list(docs.values()),'errors':list(errors.values())}
    temp=path.with_suffix('.json.tmp')
    temp.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n')
    temp.replace(path)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--max-files',type=int,default=12,help='total unique official URLs to cover')
    ap.add_argument('--delay',type=float,default=10)
    a=ap.parse_args()
    if a.delay < 10: raise SystemExit('Respect official site robots Crawl-delay: 10')
    if a.max_files < 1 or a.max_files > 250:raise SystemExit('max-files out of range')
    snapshot=json.loads(SOURCE.read_text())
    if snapshot['source'] != HOST:raise SystemExit('Unexpected original source domain')
    ordered=['/politika-konfidencialnosti-i-obrabotki-personalnyh-dannyh',
       '/ceny-i-usloviya-predostavleniya-uslug','/oficialnye-dokumenty-muzeya',
       '/stoimost','/politika-obespecheniya-usloviy-dostupnosti-dlya-invalidov-i-drugih-mobilnyh-grazhdan',
       '/finansovo-hozyaystvennaya-deyatelnost','/protivodeystvie-korrupcii']
    bypath={x['path']:x for x in snapshot['pages']}
    links={}
    for src in ordered:
        if src not in bypath:raise SystemExit('Snapshot missing category: '+src)
        for doc in bypath[src]['document_links']:
            link=doc['url']
            if not link.startswith(HOST+'/sites/default/files/'):raise SystemExit('Unsafe URL in snapshot')
            links.setdefault(link,{'url':link,'label':doc['label'],'source':src})
    ARCHIVE.mkdir(parents=True,exist_ok=True)
    path=ARCHIVE/'manifest.json'
    old=json.loads(path.read_text()) if path.exists() else {'source':HOST,'files':[],'errors':[]}
    if old['source']!=HOST:raise SystemExit('Old manifest refers to another domain')
    stored={item['url']:item for item in old['files']}
    errors={item['url']:item for item in old['errors']}
    network_count=0
    for rec in list(links.values())[:a.max_files]:
        u=rec['url']
        if u in stored:
            prior=stored[u]
            local=ARCHIVE/prior['local_name']
            if not local.is_file() or local.stat().st_size!=prior['size_bytes'] or sha256(local.read_bytes()).hexdigest()!=prior['sha256']:
                raise SystemExit('Private archival original changed unexpectedly: '+u)
            print('SKIP verified original',u.rsplit('/',1)[-1][:55],flush=True)
            errors.pop(u,None)
            continue
        if network_count:sleep(a.delay)
        network_count+=1
        ext=Path(urlparse(u).path).suffix.lower()
        if ext not in ('.pdf','.docx','.xlsx'):
            errors[u]={'url':u,'error':'unsupported_extension'}
            save(path,stored,errors)
            continue
        try:
            with urlopen(Request(u,headers={'User-Agent':'Mozilla/5.0 (MusBread public legal-source archiver)'}),timeout=30) as r:
                if r.status!=200:raise ValueError(f'HTTP {r.status}')
                size=r.headers.get('Content-Length')
                if size and int(size)>100_000_000:raise ValueError('Declared file exceeds 100MB')
                data=r.read(100_000_001)
                if len(data)>100_000_000:raise ValueError('File exceeds 100MB')
                if size and int(size)!=len(data):raise ValueError('Truncated HTTP document')
                content_type=r.headers.get('Content-Type','')
            if ext=='.pdf' and not data.startswith(b'%PDF-'):raise ValueError('PDF magic invalid')
            if ext in ('.docx','.xlsx') and not data.startswith(b'PK\x03\x04'):raise ValueError('Office OpenXML magic invalid')
            checksum=sha256(data).hexdigest()
            local=ARCHIVE/(checksum+ext)
            if local.exists():
                if sha256(local.read_bytes()).hexdigest()!=checksum:raise ValueError('SHA collision/stale file')
            else:
                tmp=local.with_suffix(ext+'.tmp')
                tmp.write_bytes(data)
                tmp.replace(local)
            file_info=dict(rec)
            file_info.update({'local_name':local.name,'sha256':checksum,
              'size_bytes':len(data),'content_type':content_type,
              'retrieved_utc':datetime.now(timezone.utc).isoformat(timespec='seconds')})
            if ext=='.pdf':
                completed=subprocess.run(['pdfinfo',str(local)],stdout=subprocess.DEVNULL,
                                         stderr=subprocess.DEVNULL,timeout=20)
                if completed.returncode!=0:raise ValueError('PDF parser rejected document')
                file_info['verified_pdfinfo']=True
            stored[u]=file_info
            errors.pop(u,None)
            print('OK',len(stored),'/',len(links),rec['label'][:50],'bytes',len(data),flush=True)
        except Exception as exc:
            errors[u]={'url':u,'error':type(exc).__name__,'details':str(exc)[:180]}
            print('FAIL',u.rsplit('/',1)[-1],type(exc).__name__,flush=True)
        save(path,stored,errors)
    print('FINAL',len(stored),'archived originals from',len(links),'source files; missing',
          len(set(links)-set(stored)), 'errors',len(errors),flush=True)
if __name__=='__main__':main()
