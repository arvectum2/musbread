#!/usr/bin/env python3
"""Capture all six official CURRENT and TRAVELING exhibition detail pages.

Only links documented in pinned museum index captures. Crawl-delay 10s.
No site media download. Fail closed for changed index or short detail pages.
"""
from __future__ import annotations
import json,re
from pathlib import Path
from datetime import datetime,timezone
from hashlib import sha256
from time import sleep
from urllib.request import Request,urlopen
from lxml import html as lx
from capture_official_museum_pages import HOST,parse
ROOT=Path(__file__).resolve().parents[1]
INDEX=ROOT/'apps/web/src/data/official-exhibition-indexes.json'
OUT=ROOT/'apps/web/src/data/official-exhibition-details.json'
GROUPS={'exhibitions-current':2,'exhibitions-traveling':4}
def main():
    indexes=json.loads(INDEX.read_text())
    if indexes['source']!=HOST or indexes['count']!=4:
        raise RuntimeError('Museum exhibition index source/count changed')
    urls=[]; seen=set()
    for item in indexes['indexes']:
        if item['slug'] not in GROUPS:continue
        if sha256(item['html'].encode()).hexdigest()!=item['html_sha256']:
            raise RuntimeError('Exhibition index html signature mismatch')
        links=item['linked_exhibitions']
        if len(links)!=GROUPS[item['slug']]:
            raise RuntimeError('Exhibition list count changed')
        for entry in links:
            path=entry['path']
            if not re.fullmatch(r'/vistavky/[0-9]{4}-[0-9]{2}-[0-9]{2}/[a-z0-9-]+',path):
                raise RuntimeError('Unexpected official exhibition URL '+str(path))
            if entry['source_url']!=HOST+path or path in seen:
                raise RuntimeError('Duplicate / unverified exhibition URL')
            seen.add(path)
            urls.append((item['slug'],entry))
    snapshot=datetime.now(timezone.utc).isoformat(timespec='seconds')
    out=[]
    for i,(category,item) in enumerate(urls):
        if i:sleep(10)
        req=Request(item['source_url'],headers={'User-Agent':'Mozilla/5.0 (MusBread museum exhibition source capture)','Accept':'text/html'})
        with urlopen(req,timeout=27) as r:
            if r.status!=200 or 'text/html' not in r.headers.get('Content-Type',''):
                raise RuntimeError('Exhibition detail URL not official HTML 200: '+item['source_url'])
            body=r.read(1_500_000).decode('utf-8','replace')
        page=parse(body,item['path'],snapshot)
        if page['text_length']<100:
            raise RuntimeError('Empty museum exhibition detail: '+item['source_url'])
        slug='museum-exhibit-'+item['path'].removeprefix('/vistavky/').replace('/','-')
        intro=' '.join(lx.fromstring('<div>'+page['html']+'</div>').text_content().split())[:245]
        page.update({'slug':slug,'category_slug':category,'index_label':item['title'],
                     'intro':intro,'photos_rights_confirmed':False})
        out.append(page)
        print('VERIFIED',i+1,'/',len(urls),category,'title',page['title'][:60],
              'characters',page['text_length'],'photos',len(page['image_links']),flush=True)
    result={'source':HOST,'snapshot_utc':snapshot,'count':len(out),'exhibitions':out,
       'media_policy':'image URLs solely retained for source/provenance, not republished'}
    tmp=OUT.with_suffix('.json.tmp')
    tmp.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    tmp.replace(OUT)
    print('SAVED',OUT,'six original museum current and traveling exhibit descriptions')
if __name__=='__main__':main()
