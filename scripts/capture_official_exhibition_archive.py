#!/usr/bin/env python3
"""Copy original historical/virtual museum exhibition texts from pinned genuine catalogs.

Read only the 24 hyperlinks already in the source-signed museum index JSON.
Preserve short and image-only source notices without OCR or fake descriptions.
Store source records/private originals on ArvectumSSD. Crawl delay >=10s.
"""
from __future__ import annotations
from datetime import datetime,timezone
from hashlib import sha256
from pathlib import Path
from time import sleep
from urllib.request import Request,urlopen
from lxml import html as lx
import json,re
from urllib.parse import urlparse
from capture_official_museum_pages import HOST,parse,url
from cache_official_museum_photos import canonical
ROOT=Path(__file__).resolve().parents[1]
INDEX=ROOT/'apps/web/src/data/official-exhibition-indexes.json'
OUT=ROOT/'apps/web/src/data/official-exhibition-archive.json'
CACHE=ROOT/'.local_archive/exhibition-archive-verified-records'
GROUPS=('exhibitions-past','exhibitions-virtual')

def capture_one(raw:str,path:str,stamp:str)->dict:
    try:
        d=parse(raw,path,stamp,min_text_length=8)
        d['image_only']=False
        return d
    except ValueError:
        root=lx.fromstring(raw)
        heads=root.xpath('//h1')
        articles=root.xpath('//article[contains(concat(" ",normalize-space(@class)," ")," node-vistavka ")]')
        if len(heads)!=1 or len(articles)!=1:
            raise RuntimeError('Museum exhibition does not have an identifiable source body '+path)
        article=articles[0]
        if ' '.join(article.text_content().split()):
            raise RuntimeError('Original exhibition has unparsed text; cannot treat as an image-only item '+path)
        images=article.xpath('.//img[@src]')
        if not 1<=len(images)<=12:raise RuntimeError('Museum exhibition has no verifiable image-only body '+path)
        photos=[]
        for img in images:
            a=img.getparent()
            candidate=a.get('href') if a.tag=='a' else img.get('src')
            source=canonical(url(candidate,HOST+path) or '')
            photos.append({'url':source,'alt':img.get('alt','')[:280]})
        empty=sha256(b'').hexdigest()
        return {'path':path,'source_url':HOST+path,
                'title':' '.join(heads[0].text_content().split()),
                'captured_utc':stamp,'html':'','html_sha256':empty,
                'text_sha256':empty,'text_length':0,
                'document_links':[],'image_links':photos,
                'image_only':True,'source_page_sha256':sha256(raw.encode()).hexdigest()}

def main():
    source=json.loads(INDEX.read_text(encoding='utf-8'))
    if source.get('source')!=HOST or source.get('count')!=4:
        raise RuntimeError('Not genuine four museum exhibition catalogues')
    items=[];seen=set();index_hashes={}
    for group in source['indexes']:
        if group['slug'] not in GROUPS:continue
        if sha256(group['html'].encode()).hexdigest()!=group['html_sha256']:
            raise RuntimeError('Museum original exhibition index digest differs')
        if len(group['linked_exhibitions'])!=12:
            raise RuntimeError('Expected museum archived/virtual catalogue of 12')
        index_hashes[group['slug']]=group['html_sha256']
        for link in group['linked_exhibitions']:
            path=link['path'];url0=link['source_url']
            if not re.fullmatch(r'/vistavky/20\d{2}-\d\d-\d\d/[a-z0-9-]+',path) or url0!=HOST+path or path in seen:
                raise RuntimeError('Unverified original exhibition URL '+path)
            seen.add(path);items.append((group['slug'],link))
    if len(items)!=24 or len(index_hashes)!=2:
        raise RuntimeError('Incomplete museum archival exhibitions linked from official index')
    CACHE.mkdir(parents=True,exist_ok=True)
    stamp=datetime.now(timezone.utc).isoformat(timespec='seconds')
    results=[];errors=[];requested=False
    for i,(category,link) in enumerate(items,1):
        path=link['path'];loc=CACHE/(sha256(path.encode()).hexdigest()+'.json')
        try:
            if loc.exists():data=json.loads(loc.read_text())
            else:
                if requested:sleep(10)
                with urlopen(Request(link['source_url'],headers={
                    'User-Agent':'Mozilla/5.0 (MusBread source-only museum exhibition archive)','Accept':'text/html'}),timeout=35) as r:
                    if r.status!=200 or 'text/html' not in r.headers.get('Content-Type',''):
                        raise RuntimeError('Not valid official source HTML')
                    raw=r.read(2_000_000).decode('utf-8','replace')
                requested=True
                data=capture_one(raw,path,stamp)
                if data['source_url']!=link['source_url']:
                    raise RuntimeError('Museum exhibition URL changed')
                tmp=loc.with_suffix('.tmp');tmp.write_text(json.dumps(data,ensure_ascii=False)+'\n');tmp.replace(loc)
            if data['source_url']!=link['source_url'] or data['path']!=path or sha256(data['html'].encode()).hexdigest()!=data['html_sha256']:
                raise RuntimeError('Cached museum source mismatch')
            if not data.get('image_only') and data['text_length']<8:
                raise RuntimeError('Empty museum exhibition detail not image-only')
            body=' '.join(lx.fromstring('<div>'+data['html']+'</div>').text_content().split())
            data.update({'slug':'museum-exhibit-'+path.removeprefix('/vistavky/').replace('/','-'),
                         'category_slug':category,'index_label':link['title'],
                         'intro':body[:245], 'photos_rights_confirmed':False,
                         'source_index_sha256':index_hashes[category]})
            results.append(data)
            print('EXHIBIT',i,'/',len(items),'OK',category,data['title'][:65],len(body),'chars',flush=True)
        except Exception as e:
            errors.append({'path':path,'error':type(e).__name__,'message':str(e)[:200]})
            print('EXHIBIT',i,'/',len(items),'SKIP',path,type(e).__name__,flush=True)
    payload={'source':HOST,'snapshot_utc':stamp,'expected':24,'count':len(results),
             'catalogue_shas':index_hashes,'exhibitions':results,'errors':errors,
             'media_policy':'Original texts only; no rights assumed for museum photographs or posters.'}
    tmp=OUT.with_suffix('.json.tmp');tmp.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n');tmp.replace(OUT)
    print('EXHIBITION_ARCHIVE_FINISHED',len(results),'/24', 'errors',len(errors),flush=True)
    if errors:raise RuntimeError('Some museum exhibition originals need a source-specific review')
if __name__=='__main__':main()
