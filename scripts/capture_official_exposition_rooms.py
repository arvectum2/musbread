#!/usr/bin/env python3
"""Explicit source-backed capture of exactly the current museum exposition rooms.

Uses the 11 official listings retained in the project, never invents exhibits,
credentials or licensing claims. No source photos are rehosted or published.
Robots.txt crawl delay of ten seconds is respected for requests.
"""
from __future__ import annotations
import argparse,json,re
from datetime import datetime,timezone
from hashlib import sha256
from pathlib import Path
from time import sleep
from urllib.parse import urlparse
from urllib.request import Request,urlopen
from lxml import html as lx
from capture_official_museum_pages import HOST,safe_html

ROOT=Path(__file__).resolve().parents[1]
LIST=ROOT/'apps/web/src/data/official-page-snapshots.json'
OUT=ROOT/'apps/web/src/data/official-exposition-rooms.json'
SLUG_RE=re.compile(r'^[a-z0-9]+(?:-[a-z0-9]+)*$')

def listing(data):
    index=next(x for x in data['pages'] if x['path']=='/ekspozicii')
    holder=lx.fromstring('<div>'+index['html']+'</div>')
    links=[]
    for a in holder.xpath('.//a[@href]'):
        uri=a.get('href')
        title=' '.join(a.text_content().split())
        prefix=HOST+'/ekspozicii/'
        if not uri.startswith(prefix):raise ValueError('Out-of-domain exposition URL')
        tail=uri[len(prefix):]
        slug=tail.rsplit('/',1)[-1]
        if not SLUG_RE.fullmatch(slug) or not title.startswith('Зал «'):
            raise ValueError('Unexpected exposition source link')
        links.append({'slug':slug,'source_url':uri,'title':title})
    if len(links)!=11 or len({x['slug'] for x in links})!=11:
        raise ValueError('Expected 11 distinct source rooms: inspect live site and listing before changing schema')
    return links

def capture(record,source,date):
    root=lx.fromstring(source)
    h1=root.xpath('//h1')
    title=' '.join(h1[0].text_content().split()) if h1 else ''
    if title!=record['title']:raise ValueError('Official room title mismatch '+record['slug']+': '+title)
    bodies=root.xpath('//*[contains(concat(" ",normalize-space(@class)," ")," field-name-body ")]')
    if len(bodies)!=1:raise ValueError('Expected one Drupal article body: '+record['slug'])
    body=bodies[0]
    plain=' '.join(body.text_content().split())
    if len(plain)<100:raise ValueError('Room exposition description unexpectedly short')
    contents=safe_html(body,record['source_url'])
    if len(contents)<100:raise ValueError('Room HTML stripped unexpectedly')
    images=[]
    for img in root.xpath('//*[contains(concat(" ",normalize-space(@class)," ")," field-name-field-foto ")]//img[@src]'):
        uri=img.get('src','')
        if uri.startswith(HOST+'/sites/default/files/') and uri.split('?')[0].lower().endswith(('.jpg','.jpeg','.png','.webp')):
            images.append({'source_url':uri,'alt':img.get('alt','')[:220]})
    if not images:
        # Historical Drupal galleries may not consistently use the same field class.
        for img in root.xpath('//article//img[@src]'):
            uri=img.get('src','')
            if uri.startswith(HOST+'/sites/default/files/') and uri.split('?')[0].lower().endswith(('.jpg','.jpeg','.png','.webp')):
                images.append({'source_url':uri,'alt':img.get('alt','')[:220]})
    images=list({x['source_url']:x for x in images}.values())
    return {
        **record,
        'captured_utc':date,
        'html':contents,
        'html_sha256':sha256(contents.encode('utf-8')).hexdigest(),
        'description_length':len(plain),
        'excerpt':' '.join(plain[:225].split()),
        'image_sources':images,
        'media_rights_confirmed':False,
    }

def main():
    a=argparse.ArgumentParser()
    a.add_argument('--delay',type=float,default=10)
    a.add_argument('--output',type=Path,default=OUT)
    opts=a.parse_args()
    if opts.delay<10:raise SystemExit('Respect official robots Crawl-delay 10')
    saved=json.loads(LIST.read_text())
    if saved['source']!=HOST:raise SystemExit('Wrong museum origin')
    items=listing(saved)
    date=datetime.now(timezone.utc).isoformat(timespec='seconds')
    rooms=[]
    for i,record in enumerate(items):
        if i:sleep(opts.delay)
        request=Request(record['source_url'],headers={'User-Agent':'Mozilla/5.0 (MusBread source-backed exposition QA)','Accept':'text/html'})
        with urlopen(request,timeout=30) as response:
            if response.status!=200 or 'text/html' not in response.headers.get('Content-Type',''):
                raise ValueError('Official museum article unavailable')
            article=response.read(1_500_000).decode('utf-8','replace')
        item=capture(record,article,date)
        rooms.append(item)
        print('OK',i+1,'/',len(items),record['title'],'text',item['description_length'],
              'source-photo refs',len(item['image_sources']),flush=True)
    result={'source':HOST,'listing_source_url':HOST+'/ekspozicii',
            'snapshot_utc':date,'rooms':rooms,'count':len(rooms),
            'policy':'Source photos are provenance only, not reproduced without review'}
    opts.output.parent.mkdir(parents=True,exist_ok=True)
    tmp=opts.output.with_suffix('.json.tmp')
    tmp.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    tmp.replace(opts.output)
    print('DONE',len(rooms),'rooms',opts.output,flush=True)
if __name__=='__main__':main()
