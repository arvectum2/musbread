#!/usr/bin/env python3
"""Snapshot 10 real museum news posts from official latest /novosty index.

Strict index/date/title/url verification. Original photos recorded as provenance,
never republished. One request per 10 seconds in respect of robots Crawl-delay.
"""
from __future__ import annotations
from datetime import datetime, timezone
from hashlib import sha256
import json, re
from pathlib import Path
from time import sleep
from urllib.request import Request, urlopen
from lxml import html as lx
from capture_official_museum_pages import HOST, parse, safe_html

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'apps/web/src/data/official-museum-news.json'
NEWS_RE=re.compile(r'^/novosty/20\d{2}-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12][0-9]|3[01])/[a-z0-9-]+$')
HEADERS={'User-Agent':'Mozilla/5.0 (MuseumBread source version capture)','Accept':'text/html'}
def fetch(path):
    with urlopen(Request(HOST+path,headers=HEADERS),timeout=26) as r:
        if r.status!=200 or 'text/html' not in r.headers.get('Content-Type',''):
            raise RuntimeError('Museum news source is not HTTP 200 HTML '+path)
        return r.read(1800000).decode('utf-8','replace')
def main():
    stamp=datetime.now(timezone.utc).isoformat(timespec='seconds')
    tree=lx.fromstring(fetch('/novosty'))
    views=tree.xpath('//*[contains(concat(" ",normalize-space(@class)," ")," view-content ")]')
    if len(views)!=1:raise RuntimeError('News index Drupal view-content structure changed')
    listing=views[0]
    links=[];seen=set()
    for a in listing.xpath('.//a[@href]'):
        path=a.get('href','')
        if not NEWS_RE.fullmatch(path):continue
        if path in seen:continue
        label=' '.join(a.text_content().split())
        if len(label)<8:raise RuntimeError('Empty news source label')
        seen.add(path)
        links.append({'path':path,'title':label,'source_url':HOST+path,'published_on':path.split('/')[2]})
    if len(links)!=10:
        raise RuntimeError('Expected precisely 10 news items on current first page, saw '+str(len(links)))
    safe=safe_html(listing,HOST+'/novosty')
    items=[]
    for i,meta in enumerate(links):
        sleep(10)
        detail=parse(fetch(meta['path']),meta['path'],stamp)
        if detail['source_url']!=meta['source_url'] or detail['title']!=meta['title'] or detail['text_length']<80:
            raise RuntimeError('Museum news headline/length mismatch for '+meta['path'])
        body=' '.join(lx.fromstring('<div>'+detail['html']+'</div>').text_content().split())
        detail.update({
            'slug':'museum-news-'+meta['path'].split('/')[2]+'-'+meta['path'].rsplit('/',1)[-1],
            'published_on':meta['published_on'],
            'intro':body[:245],
            'photos_rights_confirmed':False,
        })
        items.append(detail)
        print('VERIFIED',i+1,'/',len(links),detail['title'][:65],
              'words',len(body.split()),'images',len(detail['image_links']),flush=True)
    original={'source':HOST,'snapshot_utc':stamp,'index_path':'/novosty',
        'index_url':HOST+'/novosty','index_html_sha256':sha256(safe.encode()).hexdigest(),
        'index_html':safe,'count':len(items),'articles':items,
        'rights_note':'Original site news texts used as museum source edition. Photo URLs provenance only; source article publication date is NOT event date.'}
    tmp=OUT.with_suffix('.json.tmp')
    tmp.write_text(json.dumps(original,ensure_ascii=False,indent=2)+'\n')
    tmp.replace(OUT)
    print('SAVED',OUT,len(items),'original current museum news texts',flush=True)
if __name__=='__main__':main()
