#!/usr/bin/env python3
"""Capture actual museum exhibition listings directly from user Mac mini.
Works with museum's Drupal Views indexes (which lack field-name-body).
Lists are historical/source snapshots, not dynamic booking availability.
"""
from __future__ import annotations
import json, re
from datetime import datetime,timezone
from hashlib import sha256
from pathlib import Path
from time import sleep
from urllib.parse import urljoin, urlparse
from urllib.request import Request,urlopen
from lxml import html as lx
from capture_official_museum_pages import HOST, safe_html
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'apps/web/src/data/official-exhibition-indexes.json'
TARGETS=[
 ('exhibitions-current','/vistavky/tekushchie-vystavki'),
 ('exhibitions-traveling','/vistavky/vyezdnye-vystavki'),
 ('exhibitions-past','/vistavky/proshedshie-vystavki'),
 ('exhibitions-virtual','/vistavky/virtualnye-vystavki'),
]
def main():
    date=datetime.now(timezone.utc).isoformat(timespec='seconds')
    indexes=[]
    for i,(slug,path) in enumerate(TARGETS):
        if i:sleep(10)
        req=Request(HOST+path,headers={'User-Agent':'Mozilla/5.0 (Museum Bread research source validation)','Accept':'text/html'})
        with urlopen(req,timeout=30) as response:
            if response.status!=200 or 'text/html' not in response.headers.get('Content-Type',''):
                raise RuntimeError('Missing official exhibition page '+path)
            raw=response.read(1500000).decode('utf-8','replace')
        root=lx.fromstring(raw)
        h=root.xpath('//h1')
        heading=' '.join(h[0].text_content().split()) if h else ''
        containers=root.xpath('//*[contains(concat(" ",normalize-space(@class)," ")," view-content ")]')
        if not containers:raise RuntimeError('Exhibition source view-content missing: '+path)
        section=containers[0]
        raw_text=' '.join(section.text_content().split())
        source_html=safe_html(section,HOST+path)
        if len(raw_text)<20 or len(source_html)<30:raise RuntimeError('Empty exhibition source '+path)
        links=[];images=[]
        for a in section.xpath('.//a[@href]'):
            href=urljoin(HOST+path,a.get('href',''))
            if href.startswith(HOST+'/vistavky/') and href != HOST+path:
                label=' '.join(a.text_content().split())
                if href not in {i['source_url'] for i in links}:
                    links.append({'source_url':href,'title':label,'path':urlparse(href).path})
        for link in links:
            # The Drupal View prints title, date text, then title again
            # as the linked label. Extract the actual displayed interval
            # rather than invent opening dates from URL timestamps.
            first=raw_text.find(link['title'])
            second=raw_text.find(link['title'],first+len(link['title'])) if first>=0 else -1
            between=raw_text[first+len(link['title']):second].strip() if second>=0 else ''
            link['date_text']=between if len(between)<75 and re.search(r'20\d\d',between) else None
        for img in section.xpath('.//img[@src]'):
            u=urljoin(HOST+path,img.get('src',''))
            if u.startswith(HOST+'/'):
                images.append({'url':u,'alt':img.get('alt','')[:250]})
        item={
            'slug':slug,'path':path,'source_url':HOST+path,
            'title':heading,'captured_utc':date,
            'html':source_html,'html_sha256':sha256(source_html.encode()).hexdigest(),
            'raw_text_sha256':sha256(raw_text.encode()).hexdigest(),
            'text_length':len(raw_text),
            'linked_exhibitions':links,'image_links':images,
            'images_rights_confirmed':False
        }
        indexes.append(item)
        print('VERIFIED',slug,heading,'items',len(links),'photos',len(images),'text',len(raw_text),flush=True)
    out={'source':HOST,'snapshot_utc':date,'count':len(indexes),'indexes':indexes,
        'photos':'Original image URLs preserved solely for provenance. Images not republished.'}
    tmp=OUT.with_suffix('.json.tmp')
    tmp.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
    tmp.replace(OUT)
    print('SAVED',OUT)
if __name__=='__main__':main()
