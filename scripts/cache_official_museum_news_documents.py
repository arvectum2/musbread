#!/usr/bin/env python3
"""Fetch only genuine original PDF/DOCX files *actually linked* by museum news.

Historical orders are archival (never current museum rules). Verify exact article
source HTML and literal document hyperlink before fetching through user's Mac.
Respect original museum crawl delay 10s and store original bytes privately.
"""
from __future__ import annotations
import argparse,hashlib,json,re,time
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import Request,urlopen
from urllib.error import HTTPError
from lxml import html
ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'apps/web/src/data'
OUT=ROOT/'.local_archive/news-original-documents'
MANIFEST=OUT/'manifest.json'
DOMAIN='https://muzei-xleb.ru'
ALLOWED_EXT={'.pdf':b'%PDF','.docx':b'PK'}

def source_docs():
    # These are separately source-verified original museum news records.
    docs={}
    for filename in ['official-museum-news.json','official-museum-news-archive.json']:
        data=json.loads((DATA/filename).read_text(encoding='utf-8'))
        if data['source']!=DOMAIN:raise RuntimeError('Unknown museum source '+filename)
        for article in data['articles']:
            if hashlib.sha256(article['html'].encode()).hexdigest()!=article['html_sha256']:
                raise RuntimeError('Unverified museum news HTML source '+article['source_url'])
            actual={a.get('href') for a in html.fragment_fromstring(article['html'],create_parent='div').xpath('.//a[@href]')}
            for item in article.get('document_links',[]):
                u=urlsplit(item['url']);suffix=Path(u.path).suffix.lower()
                if (u.hostname!='muzei-xleb.ru' or u.scheme not in ('https','http')
                    or suffix not in ALLOWED_EXT or not u.path.startswith('/sites/default/files/')
                    or u.query or item['url'] not in actual):
                    raise RuntimeError('Invalid/unstated museum historical document '+str(item))
                canonical=DOMAIN+u.path
                if canonical not in docs:
                    docs[canonical]={'url':canonical,'legacy_source_url':item['url'],
                                     'label':item['label'],'referer':article['source_url']}
    return docs

def download(limit:int|None=None,delay:float=10):
    if delay<10:raise ValueError('Museum robots crawl-delay 10 required')
    originals=source_docs()
    if not originals:
        print('HISTORICAL_NEWS_DOCUMENTS none in source-verified articles');return
    OUT.mkdir(parents=True,exist_ok=True)
    prior=json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {'source':DOMAIN,'files':[],'errors':[]}
    if prior.get('source')!=DOMAIN:raise RuntimeError('Unknown local original document manifest')
    known={r['url']:r for r in prior['files']}
    saved=[];missing=[];last_http=False
    for i,(url,meta) in enumerate(sorted(originals.items()),1):
        existing=known.get(url)
        if existing:
            original=OUT/existing['local_name'];sha=existing['sha256']
            if not original.is_file() or original.stat().st_size!=existing['size_bytes'] or hashlib.sha256(original.read_bytes()).hexdigest()!=sha:
                raise RuntimeError('Cached original museum document corrupted '+url)
            saved.append(existing)
            print('PRESERVED_NEWS_DOC',i,len(originals),url,flush=True)
            continue
        if limit is not None and len(saved)>=limit:break
        if last_http:time.sleep(delay)
        try:
            with urlopen(Request(url,headers={'User-Agent':'Mozilla/5.0 (MuseumBread archive transfer)','Accept':'application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document'}),timeout=50) as response:
                if response.status!=200:raise RuntimeError('Museum document not HTTP 200 '+url)
                body=response.read(60*1024*1024+1)
        except HTTPError as exc:
            if exc.code!=404:raise
            missing.append({**meta,'url':url,'http_status':404,'source_confirmation':'original museum URL returned HTTP 404; do not invent PDF bytes'})
            last_http=True
            print('SOURCE_DOCUMENT_UNAVAILABLE_404',url,'linked_from',meta['referer'],flush=True)
            continue
        last_http=True
        extension=Path(urlsplit(url).path).suffix.lower()
        if not 0<len(body)<60*1024*1024 or not body.startswith(ALLOWED_EXT[extension]):
            raise RuntimeError('Museum PDF/DOCX original bytes/type mismatch '+url)
        sha=hashlib.sha256(body).hexdigest();name=sha+extension
        (OUT/name).write_bytes(body)
        record={**meta,'local_name':name,'sha256':sha,'size_bytes':len(body)}
        saved.append(record)
        print('DOWNLOADED_GENUINE_NEWS_DOC',i,len(originals),url,len(body),'bytes',flush=True)
    snapshot={'source':DOMAIN,'count':len(saved),'files':saved,'errors':[]}
    if len(saved)+len(missing)==len(originals):
        if saved:MANIFEST.write_text(json.dumps(snapshot,ensure_ascii=False,indent=2)+'\n')
        (OUT/'unavailable.json').write_text(json.dumps({'source':DOMAIN,'count':len(missing),'files':missing},ensure_ascii=False,indent=2)+'\n')
    print('GENUINE_MUSEUM_NEWS_DOC_COMPLETE',len(saved),'downloaded',len(missing),'historical sources already HTTP 404','of',len(originals),flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--limit',type=int);p.add_argument('--delay',type=float,default=10)
    args=p.parse_args();download(args.limit,args.delay)
