#!/usr/bin/env python3
"""Source-verify museum's historical /node/N links from genuine news.

Only a literal source-verified news hyperlink authorizes a GET. Report status,
final effective URL and original H1; never invent target exhibitions, redirect
rules, or publish unverifiable content. Uses Mac mini network and crawl-delay.
"""
from __future__ import annotations
import argparse,json,re,time,hashlib
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.error import HTTPError
from urllib.parse import urlsplit
from lxml import html
ROOT=Path(__file__).resolve().parents[1]
CSV=ROOT/'docs/source-migration/NEWS_ARCHIVE_NESTED_ORIGINAL_LINKS_20261018.csv'
OUT=ROOT/'.local_archive/news-linked-nodes'
MANIFEST=OUT/'manifest.json'
DOMAIN='https://muzei-xleb.ru'

def get_source_node_paths():
    import csv
    with CSV.open(encoding='utf-8-sig',newline='') as f:
        items=list(csv.DictReader(f,delimiter=';'))
    from collections import Counter
    frequency=Counter(x['original_link_path'] for x in items if x['content_check']=='legacy-node')
    paths=sorted(frequency,key=lambda x:(-frequency[x],int(x.split('/')[-1])))
    if not all(re.fullmatch(r'/node/\d+',x) for x in paths):raise ValueError('Unexpected source original node paths')
    return paths

def main(*,limit:int|None,delay:float):
    if delay<10:raise ValueError('Museum source crawl-delay minimum 10s')
    paths=get_source_node_paths()
    OUT.mkdir(parents=True,exist_ok=True)
    earlier=json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {'source':DOMAIN,'nodes':[]}
    if earlier['source']!=DOMAIN:raise RuntimeError('Different museum node source')
    known={x['path']:x for x in earlier['nodes']}
    checked=[];requests=0
    for path in paths:
        if path in known:
            checked.append(known[path]);continue
        if limit is not None and requests>=limit:break
        if requests:time.sleep(delay)
        try:
            with urlopen(Request(DOMAIN+path,headers={'User-Agent':'Mozilla/5.0 (MuseumBread historical original-link audit)','Accept':'text/html'}),timeout=30) as response:
                raw=response.read(1_500_000)
                record={'path':path,'status':response.status,
                        'resolved_url':response.geturl(),
                        'content_type':response.headers.get('Content-Type',''),
                        'html_sha256':hashlib.sha256(raw).hexdigest(),
                        'original_title':'','text_chars':0,'html_canonical':''}
                if 'text/html' in record['content_type']:
                    tree=html.fromstring(raw)
                    headers=tree.xpath('//h1')
                    record['original_title']=' '.join(headers[0].text_content().split()) if headers else ''
                    canon=tree.xpath('//link[translate(@rel,"ABCDEFGHIJKLMNOPQRSTUVWXYZ","abcdefghijklmnopqrstuvwxyz")="canonical"]/@href')
                    record['html_canonical']=canon[0] if canon else ''
                    body=tree.xpath('//*[contains(concat(" ",normalize-space(@class)," ")," field-name-body ")]')
                    record['text_chars']=len(' '.join(body[0].text_content().split())) if body else 0
                    (OUT/(path.split('/')[-1]+'.html')).write_bytes(raw)
        except HTTPError as err:
            record={'path':path,'status':err.code,'resolved_url':err.geturl(),'content_type':err.headers.get('Content-Type',''),'html_sha256':'','original_title':'','text_chars':0,'html_canonical':''}
        checked.append(record);requests+=1
        print('ORIGINAL_MUSEUM_NODE_CHECK',path,'HTTP',record['status'],'effective',record['resolved_url'],'H1',record['original_title'][:85],flush=True)
        MANIFEST.write_text(json.dumps({'source':DOMAIN,'verified':len(checked),'nodes':checked},ensure_ascii=False,indent=2)+'\n')
    print('ORIGINAL_NEWS_NUMERIC_LINKS',len(checked),'of',len(paths),'verified via Mac mini, no assumptions',flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--limit',type=int);p.add_argument('--delay',type=float,default=10)
    a=p.parse_args();main(limit=a.limit,delay=a.delay)
