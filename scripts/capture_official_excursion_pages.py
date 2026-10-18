#!/usr/bin/env python3
"""Capture official excursion categories only from explicitly verified museum URLs.

Mac mini direct HTTP; robots Crawl-delay 10 seconds; no images are republished.
"""
from __future__ import annotations
import json
from pathlib import Path
from datetime import datetime,timezone
from time import sleep
from urllib.request import Request,urlopen
from capture_official_museum_pages import HOST,parse

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'apps/web/src/data/official-excursion-pages.json'
PAGES=[
 ('/obzornaya-ekskursiya','excursion-overview'),
 ('/interaktivnye-zanyatiya','excursion-interactive'),
 ('/tematicheskie-ekskursii','excursion-thematic'),
 ('/teatralizovannye-ekskursii','excursion-theatrical'),
]
def main():
    source=[];stamp=datetime.now(timezone.utc).isoformat(timespec='seconds')
    for i,(path,slug) in enumerate(PAGES):
        if i:sleep(10)
        req=Request(HOST+path,headers={'User-Agent':'Mozilla/5.0 (MusBread source-backed prototype; manual QA)','Accept':'text/html'})
        with urlopen(req,timeout=25) as response:
            if response.status!=200 or 'text/html' not in response.headers.get('Content-Type',''):
                raise ValueError('Museum URL not HTML 200: '+path)
            doc=response.read(1_500_000).decode('utf-8','replace')
        record=parse(doc,path,stamp)
        if record['text_length']<100 or not record['title']:
            raise ValueError('Source excursion page unexpectedly empty '+path)
        record['cms_slug']=slug
        record['photos_rights_confirmed']=False
        source.append(record)
        print('CAPTURED',slug,'title',record['title'],'text',record['text_length'],
              'photos',len(record['image_links']),'docs',len(record['document_links']),flush=True)
    result={'source':HOST,'snapshot_utc':stamp,'pages':source,'count':len(source),
        'media_policy':'Only photo URL metadata; do not display or republish without permission'}
    tmp=OUT.with_suffix('.json.tmp')
    tmp.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    tmp.replace(OUT)
    print('SAVED',OUT)
if __name__=='__main__':main()
