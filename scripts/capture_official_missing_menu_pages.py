#!/usr/bin/env python3
"""Capture only missing live original navigation pages; no extra PDF/OCR work.
Manual, source-verified, 10s delay between requests per museum robots.txt.
"""
from __future__ import annotations
from datetime import datetime,timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request,urlopen
from time import sleep
from hashlib import sha256
from lxml import html as lx
import json
from capture_official_museum_pages import HOST,ROOT,parse

OUT=ROOT/'apps/web/src/data/official-museum-menu-gaps.json'
TARGETS=[
  '/uchetnaya-politika',
  '/protivodeystvie-terrorizmu',
  '/antimonopolnyy-komplaens',
  '/informaciya-dlya-dariteley',
  '/gostevaya-kniga',
  '/adres',
  '/covid-19',
  '/dokumenty',
]
def main()->None:
    now=datetime.now(timezone.utc).isoformat(timespec='seconds')
    items=[];errors=[];delay=10
    for i,path in enumerate(TARGETS):
        if i:sleep(delay)
        req=Request(HOST+path,headers={'User-Agent':'Mozilla/5.0 (MusBread museum navigation source preservation)','Accept':'text/html'})
        try:
            with urlopen(req,timeout=25) as f:
                if f.status!=200 or 'text/html' not in f.headers.get('Content-Type',''):
                    raise ValueError('Expected 200 HTML from original website')
                source=f.read(2_000_000).decode('utf-8','replace')
            record=parse(source,path,now)
            # Only editorial prose from Drupal field-name-body is allowed.
            # Never archive guest-book visitor postings/comments or any forms.
            if path=='/gostevaya-kniga':
                tree=lx.fromstring(source)
                fields=tree.xpath('//*[contains(concat(" ",normalize-space(@class)," ")," field-name-body ")]')
                if not fields:
                    raise ValueError('Guestbook page has no official editorial article body; skip user submitted comments')
            items.append(record)
            print('OK',path,record['text_length'],'chars',len(record['document_links']),'docs',flush=True)
        except (Exception) as e:
            errors.append({'path':path,'reason':type(e).__name__})
            print('NO ARTICLE',path,type(e).__name__,flush=True)
    if len(items)<3:raise SystemExit('Too few actual validated original articles; source not overwritten')
    payload={'source':HOST,'captured_utc':now,'targets':TARGETS,'count':len(items),
             'pages':items,'not_articles':errors}
    tmp=OUT.with_suffix('.json.tmp')
    tmp.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    tmp.replace(OUT)
    print('SAVED',len(items),'verified articles',len(errors),'no article',OUT,flush=True)
if __name__=='__main__':main()
