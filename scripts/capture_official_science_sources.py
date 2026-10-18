#!/usr/bin/env python3
"""User Mac mini direct capture of actual museum scientific-organization pages.

The official source only has a fund acquisition policy and scientific
methodological council papers. We do not reclassify these as academic
research papers, conference proceedings, or artifact catalog records.
"""
from __future__ import annotations
import json
from datetime import datetime,timezone
from hashlib import sha256
from pathlib import Path
from time import sleep
from urllib.parse import urljoin,urlparse
from urllib.request import Request,urlopen
from lxml import html as lx
from capture_official_museum_pages import HOST,safe_html
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'apps/web/src/data/official-science-sources.json'
PAGES=[
 ('science-organization','/nauchno-organizacionnaya-deyatelnost'),
 ('science-methodical-council','/nauchno-metodicheskiy-sovet'),
]
def main():
    now=datetime.now(timezone.utc).isoformat(timespec='seconds')
    out=[]
    for i,(slug,path) in enumerate(PAGES):
        if i:sleep(10)
        req=Request(HOST+path,headers={'User-Agent':'Mozilla/5.0 (MuseumBread verified scientific materials, no browser automation)','Accept':'text/html'})
        with urlopen(req,timeout=25) as r:
            if r.status!=200 or 'text/html' not in r.headers.get('Content-Type',''):
                raise ValueError('Official museum science source unavailable: '+path)
            raw=r.read(1500000).decode('utf-8','replace')
        root=lx.fromstring(raw)
        title=' '.join(root.xpath('//h1')[0].text_content().split())
        nodes=root.xpath('//article[contains(concat(" ",normalize-space(@class)," ")," node-page ")]')
        if len(nodes)!=1:raise ValueError('Museum source article layout changed '+path)
        node=nodes[0]
        info=node.xpath('.//div[contains(concat(" ",normalize-space(@class)," ")," content ")]')
        target=info[0] if info else node
        text=' '.join(target.text_content().split())
        if len(text)<80:raise ValueError('Original science document listing empty '+path)
        html=safe_html(target,HOST+path)
        files=[]
        for a in node.xpath('.//a[@href]'):
            url=urljoin(HOST+path,a.get('href',''))
            parsed=urlparse(url)
            if parsed.hostname!='muzei-xleb.ru' or not parsed.path.lower().endswith(('.pdf','.doc','.docx','.xls','.xlsx')):
                continue
            files.append({'url':url,'label':' '.join(a.text_content().split()),'format':parsed.path.rsplit('.',1)[-1].lower()})
        if len(files)!=(1 if i==0 else 1):
            raise ValueError('Official science documents changed count')
        if sha256(html.encode()).hexdigest()==sha256(b'').hexdigest():
            raise ValueError('Missing source scientific content')
        out.append({'slug':slug,'path':path,'source_url':HOST+path,'captured_utc':now,
            'title':title,'html':html,'html_sha256':sha256(html.encode()).hexdigest(),
            'text_sha256':sha256(text.encode()).hexdigest(),
            'text_length':len(text),'documents':files,'photos_rights_confirmed':False})
        print('VERIFIED',title,'text',len(text),'docs',len(files),flush=True)
    result={'source':HOST,'snapshot_utc':now,'count':len(out),'pages':out,
        'classification':'Administrative scientific activity documents only. No invented publications, conferences, collection objects or researcher privileges.'}
    temp=OUT.with_suffix('.json.tmp')
    temp.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    temp.replace(OUT)
    print('SAVED',OUT)
if __name__=='__main__':main()
