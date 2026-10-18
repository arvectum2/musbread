#!/usr/bin/env python3
"""Capture ONLY two official museum guidance pages with provenance.

No legal rules are manufactured; sources stay museum-owned, live content.
Runs from authorized Mac mini, respects 10s Crawl-delay.
"""
from __future__ import annotations
import json
from datetime import datetime,timezone
from pathlib import Path
from time import sleep
from urllib.request import Request,urlopen
from capture_official_museum_pages import HOST,parse
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'apps/web/src/data/official-visitor-guidance.json'
PAGES=['/ekskursii','/chasy-raboty']

def main():
    found=[]
    stamp=datetime.now(timezone.utc).isoformat(timespec='seconds')
    for i,path in enumerate(PAGES):
        if i:sleep(10)
        req=Request(HOST+path,headers={'User-Agent':'Mozilla/5.0 (MusBread museum-guidance verifier; manual request)','Accept':'text/html'})
        with urlopen(req,timeout=30) as r:
            assert r.status==200 and 'text/html' in r.headers.get('Content-Type','')
            body=r.read(1_500_000).decode('utf-8','replace')
        entry=parse(body,path,stamp)
        if entry['source_url']!=HOST+path or len(entry['html'])<100:
            raise ValueError('Unexpected official museum page for '+path)
        found.append(entry)
        print('VERIFIED',entry['source_url'],'text length',entry['text_length'],'documents',len(entry['document_links']),flush=True)
    payload={'source':HOST,'snapshot_utc':stamp,'count':len(found),'pages':found}
    tmp=OUT.with_suffix('.json.tmp')
    tmp.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n')
    tmp.replace(OUT)
    print('CAPTURED',OUT,'pages',len(found))
if __name__=='__main__':main()
