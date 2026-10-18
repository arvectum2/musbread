#!/usr/bin/env python3
"""Direct Mac mini capture of program detail URLs shown in museum excursion menus.

The museum's current linked pages are the only authority; no titles,
ticket prices, school ages or gallery pictures are invented by this script.
Respect robots Crawl-delay 10s. On failure do not overwrite existing output.
"""
from __future__ import annotations
import json,re
from datetime import datetime,timezone
from pathlib import Path
from time import sleep
from urllib.request import Request,urlopen
from lxml import html as lx
from capture_official_museum_pages import HOST,parse
ROOT=Path(__file__).resolve().parents[1]
CATALOG=ROOT/'apps/web/src/data/official-excursion-pages.json'
OUT=ROOT/'apps/web/src/data/official-excursion-programs.json'
CAT_PREFIX='/ekskursii/'
SLUG=re.compile('^[a-z0-9]+(?:-[a-z0-9]+)*$')

def entries():
    src=json.loads(CATALOG.read_text())
    if src['source']!=HOST or src['count']!=4:raise RuntimeError('Missing original museum section indexes')
    items=[]
    seen_urls=set()
    for section in src['pages']:
        html=section['html']
        if section['html_sha256']!=__import__('hashlib').sha256(html.encode()).hexdigest():
            raise RuntimeError('Excursion index hash invalid')
        dom=lx.fromstring('<div>'+html+'</div>')
        for a in dom.xpath('.//a[@href]'):
            url=a.get('href','')
            if not url.startswith(HOST+CAT_PREFIX):continue
            stem=url.removeprefix(HOST+CAT_PREFIX)
            if not SLUG.fullmatch(stem):raise RuntimeError('Unexpected program URL: '+url)
            label=' '.join(a.text_content().split())
            if len(label)<5:raise RuntimeError('Empty source program label')
            # The thematic museum index links twice to the same program.
            # Keep exactly one CMS entry per official program URL.
            if url in seen_urls:continue
            seen_urls.add(url)
            items.append({'source_url':url,'path':CAT_PREFIX+stem,
                          'slug':'museum-tour-'+stem,
                          'source_label':label,'category_slug':section['cms_slug']})
    urls=[x['source_url'] for x in items]
    if len(items)!=17 or len(set(urls))!=len(urls):
        raise RuntimeError('Expected 17 distinct source programs (18 old-site link occurrences), inspect index changes')
    return items

def main():
    source=entries()
    stamp=datetime.now(timezone.utc).isoformat(timespec='seconds')
    pages=[]
    for i,item in enumerate(source):
        if i:sleep(10)
        req=Request(item['source_url'],headers={'User-Agent':'Mozilla/5.0 (MusBread verified museum program capture)','Accept':'text/html'})
        with urlopen(req,timeout=30) as r:
            if r.status!=200 or 'text/html' not in r.headers.get('Content-Type',''):
                raise RuntimeError('Official program page is no longer HTML: '+item['source_url'])
            text=r.read(1_500_000).decode('utf-8','replace')
        page=parse(text,item['path'],stamp)
        if page['text_length']<85:raise RuntimeError('Official program has insufficient description '+item['source_url'])
        page.update({x:item[x] for x in ('slug','category_slug','source_label')})
        page['intro']=' '.join(lx.fromstring('<div>'+page['html']+'</div>').text_content().split())[:250]
        page['photos_rights_confirmed']=False
        pages.append(page)
        print('VERIFIED',i+1,'/',len(source),page['title'][:75],'characters',page['text_length'],'images',len(page['image_links']),flush=True)
    result={'source':HOST,'snapshot_utc':stamp,'count':len(pages),'programs':pages,
            'rights':'Museum source photo URLs are provenance ONLY; no photo publication approved'}
    tmp=OUT.with_suffix('.json.tmp')
    tmp.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    tmp.replace(OUT)
    print('SAVED',OUT,len(pages),'genuine program descriptions',flush=True)
if __name__=='__main__':main()
