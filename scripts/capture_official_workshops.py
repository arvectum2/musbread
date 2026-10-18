#!/usr/bin/env python3
"""Capture real museum master class index and 12 linked detail pages over Mac mini.
Only original texts/URL hashes are stored; no museum photos are published.
Network delays honour official robots 10sec crawl-delay.
"""
from __future__ import annotations
import json,re
from pathlib import Path
from time import sleep
from datetime import datetime, timezone
from urllib.request import Request,urlopen
from lxml import html as lx
from capture_official_museum_pages import HOST,parse
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'apps/web/src/data/official-workshop-pages.json'
MASTER='/master-klassy'
SLUG=re.compile(r'^/[a-z0-9-]+/[a-z0-9-]+$')
def get(path:str,stamp:str)->dict:
    req=Request(HOST+path,headers={'User-Agent':'Mozilla/5.0 (MusBread source verification; one-time snapshot)','Accept':'text/html'})
    with urlopen(req,timeout=30) as response:
        if response.status!=200 or 'text/html' not in response.headers.get('Content-Type',''):
            raise RuntimeError('Museum URL no longer serves official HTML '+path)
        body=response.read(2_000_000).decode('utf-8','replace')
    return parse(body,path,stamp)
def main():
    stamp=datetime.now(timezone.utc).isoformat(timespec='seconds')
    mainpage=get(MASTER,stamp)
    dom=lx.fromstring('<div>'+mainpage['html']+'</div>')
    programs=[];seen=set()
    for anchor in dom.xpath('.//a[@href]'):
        url=anchor.get('href','');title=' '.join(anchor.text_content().split())
        if not url.startswith(HOST+'/'):continue
        path=url.removeprefix(HOST)
        if not SLUG.fullmatch(path) or not path.startswith(('/master-klassy/','/ekskursii/')):continue
        if url in seen:continue
        seen.add(url)
        programs.append({'url':url,'path':path,'source_label':title,'slug':'museum-workshop-'+path.split('/')[-1]})
    if len(programs)!=12 or len({x['slug'] for x in programs})!=12:
        raise RuntimeError('Unexpected official master class catalogue, expected exactly 12 unique source URLs: '+str(len(programs)))
    results=[]
    for i,item in enumerate(programs):
        sleep(10)
        page=get(item['path'],stamp)
        if page['text_length']<80 or page['source_url']!=item['url']:
            raise RuntimeError('Short/redirected museum workshop '+item['url'])
        text=' '.join(lx.fromstring('<div>'+page['html']+'</div>').text_content().split())
        page.update({'slug':item['slug'],'source_label':item['source_label'],
                     'intro':text[:245],'photos_rights_confirmed':False})
        results.append(page)
        print('VERIFIED',i+1,'/',len(programs),page['title'][:55],page['text_length'],'photos',len(page['image_links']),flush=True)
    mainpage['photos_rights_confirmed']=False
    data={'source':HOST,'snapshot_utc':stamp,'index':mainpage,'count':len(results),'programs':results,
          'photo_policy':'Only link metadata for source integrity; original pictures not cleared for republication'}
    tmp=OUT.with_suffix('.json.tmp')
    tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    tmp.replace(OUT)
    print('SAVED',OUT,'verified unique workshops',len(results),flush=True)
if __name__=='__main__':main()
