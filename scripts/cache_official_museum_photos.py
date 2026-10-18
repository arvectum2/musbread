#!/usr/bin/env python3
"""Download only real original image files from source-verified published museum pages.

Crawl-delay: 10 seconds between sequential HTTP requests. No generation,
stock imagery, OCR, face recognition, or speculative metadata. Store originals
privately on Mac mini ArvectumSSD; public rights require separate review.
"""
from __future__ import annotations
from datetime import datetime,timezone
from hashlib import sha256
from pathlib import Path
from time import monotonic,sleep
from urllib.parse import urlparse
from urllib.request import Request,urlopen
import argparse,json,re,struct

ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'apps/web/src/data'
OUT=ROOT/'.local_archive/museum-official-photos'
MANIFEST=OUT/'manifest.json'
HOST='https://muzei-xleb.ru'
MAX_SIZE=12_000_000
# Only source-verified museum editorial images: up to three original
# program/room photos, all 15 historical building illustrations and known
# original exhibition images. No generated/stock/placeholder imagery.
SOURCES=(('official-workshop-pages.json','programs'),
         ('official-excursion-programs.json','programs'))

def canonical(raw:str)->str:
    u=urlparse(raw)
    if u.scheme!='https' or u.hostname!='muzei-xleb.ru':
        raise ValueError('Only original museum domain')
    clean=re.sub(r'^/sites/default/files/styles/[^/]+/public/',
                 '/sites/default/files/',u.path)
    if not clean.startswith('/sites/default/files/') or not re.search(r'\.(png|jpe?g|webp)$',clean,re.I):
        raise ValueError('Only published uploaded museum raster photos')
    return HOST+clean

def queue()->list[dict]:
    result=[];seen=set()
    # First pass: one genuine photo per program; later passes fill a real
    # two/three-photo gallery, without duplicating any original URL.
    for image_index in range(3):
        for filename,key in SOURCES:
            d=json.loads((SRC/filename).read_text(encoding='utf-8'))
            if d.get('source')!=HOST:raise ValueError('Changed original image data source')
            for entry in d[key]:
                slug=entry.get('slug') or entry.get('cms_slug')
                source_url=entry.get('source_url')
                if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*',slug or ''):
                    raise ValueError('Malformed source CMS slug')
                if not source_url or urlparse(source_url).hostname!='muzei-xleb.ru':
                    raise ValueError('Malformed original page URL')
                if len(entry.get('image_links',[]))<=image_index:continue
                photo=entry['image_links'][image_index]
                raw=photo.get('url','')
                url=canonical(raw)
                if url in seen:continue
                seen.add(url)
                result.append({
                    'cms_slug':slug,'title':entry['title'],
                    'source_page_url':source_url,
                    'source_image_url':raw,'source_image_index':image_index,
                    'original_url':url,
                    'source_alt':photo.get('alt',''),
                    'source_snapshot':filename,
                    'source_html_sha256':entry.get('html_sha256'),
                })
    # All eleven existing permanent museum rooms: first authentic photograph
    # per existing editable page. Additional real room photos are appended
    # after the 93-image stable prefix to avoid re-downloading originals.
    rooms=json.loads((SRC/'official-exposition-rooms.json').read_text(encoding='utf-8'))
    if rooms.get('source')!=HOST:raise ValueError('Changed rooms source')
    for room in rooms['rooms']:
        if not room.get('image_sources'):continue
        image=room['image_sources'][0]
        url=canonical(image['source_url'])
        if url not in seen:
            seen.add(url)
            result.append({
                'cms_slug':room['slug'],'title':room['title'],
                'source_page_url':room['source_url'],
                'source_image_url':image['source_url'],
                'source_image_index':0,'original_url':url,
                'source_alt':image.get('alt',''),
                'source_snapshot':'official-exposition-rooms.json',
                'source_html_sha256':room['html_sha256'],
            })
    # Only the six current/travelling exhibition images tied 1-to-1 to
    # real detailed CMS exhibitions; do not invent a relation for archives.
    indices=json.loads((SRC/'official-exhibition-indexes.json').read_text(encoding='utf-8'))
    details=json.loads((SRC/'official-exhibition-details.json').read_text(encoding='utf-8'))
    if indices.get('source')!=HOST or details.get('source')!=HOST:
        raise ValueError('Changed exhibition source')
    by_url={x['source_url']:x for x in details['exhibitions']}
    for exhibition_index in indices['indexes']:
        if exhibition_index['slug'] not in ('exhibitions-current','exhibitions-traveling'):continue
        links=exhibition_index['linked_exhibitions'];photos=exhibition_index['image_links']
        if len(links)!=len(photos):raise ValueError('Current exhibition photo order incomplete')
        for i,(link,photo) in enumerate(zip(links,photos)):
            actual=by_url.get(link['source_url'])
            if actual is None or actual['title']!=link['title']:
                raise ValueError('Exhibition cover cannot be matched to real museum page')
            url=canonical(photo['url'])
            if url in seen:continue
            seen.add(url)
            result.append({
                'cms_slug':actual['slug'],'title':actual['title'],
                'source_page_url':actual['source_url'],
                'source_image_url':photo['url'],'source_image_index':i,
                'original_url':url,'source_alt':photo.get('alt',''),
                'source_snapshot':'official-exhibition-indexes.json',
                'source_html_sha256':actual['html_sha256'],
            })
    # Museum building history: actual historical portraits and architectural
    # photographs, not generated art or invented captions. Keep original
    # first-eight indices stable; append the remaining seven below.
    pages=json.loads((SRC/'official-page-snapshots.json').read_text(encoding='utf-8'))
    building=[x for x in pages['pages'] if x['path']=='/istoriya-zdaniya']
    if len(building)!=1:raise ValueError('Original building-history source missing')
    building=building[0]
    for i,photo in enumerate(building['image_links'][:8]):
        url=canonical(photo['url'])
        if url in seen:continue
        seen.add(url)
        result.append({
            'cms_slug':'building-history','title':building['title'],
            'source_page_url':building['source_url'],
            'source_image_url':photo['url'],'source_image_index':i,
            'original_url':url,'source_alt':photo.get('alt',''),
            'source_snapshot':'official-page-snapshots.json',
            'source_html_sha256':building['html_sha256'],
        })
    # Archive and virtual exhibition catalogues include real museum object
    # thumbnails with original museum captions. The original CMS category
    # page remains the owner; the item is not misattributed to a fictional
    # or nonexistent detailed exhibition.
    for exhibition_index in indices['indexes']:
        if exhibition_index['slug'] not in ('exhibitions-past','exhibitions-virtual'):continue
        for i,photo in enumerate(exhibition_index['image_links'][:4]):
            url=canonical(photo['url'])
            if url in seen:continue
            seen.add(url)
            result.append({
                'cms_slug':exhibition_index['slug'],
                'title':exhibition_index['title'],
                'source_page_url':exhibition_index['source_url'],
                'source_image_url':photo['url'],'source_image_index':i,
                'original_url':url,'source_alt':photo.get('alt',''),
                'source_snapshot':'official-exhibition-indexes.json',
                'source_html_sha256':exhibition_index['html_sha256'],
            })
    # Continue the ORIGINAL museum content migration beyond the first
    # photographed cover of each of the 11 rooms. Keep the stable queue prefix
    # so the initial 93 downloaded photographs need not be fetched again.
    for room in rooms['rooms']:
        for i in (1,2):
            if i>=len(room['image_sources']):continue
            image=room['image_sources'][i]
            url=canonical(image['source_url'])
            if url in seen:continue
            seen.add(url)
            result.append({
                'cms_slug':room['slug'],'title':room['title'],
                'source_page_url':room['source_url'],
                'source_image_url':image['source_url'],
                'source_image_index':i,'original_url':url,
                'source_alt':image.get('alt',''),
                'source_snapshot':'official-exposition-rooms.json',
                'source_html_sha256':room['html_sha256'],
            })
    # Preserve every actual documented illustration of the historic building.
    for i,photo in enumerate(building['image_links'][8:],start=8):
        url=canonical(photo['url'])
        if url in seen:continue
        seen.add(url)
        result.append({
            'cms_slug':'building-history','title':building['title'],
            'source_page_url':building['source_url'],
            'source_image_url':photo['url'],'source_image_index':i,
            'original_url':url,'source_alt':photo.get('alt',''),
            'source_snapshot':'official-page-snapshots.json',
            'source_html_sha256':building['html_sha256'],
        })
    # Remaining genuine original images in the 11 existing rooms, indices
    # 3 onwards. Append AFTER the 122 already imported entries, preserving
    # source ordering and stable previous provenance. No URL substitutions.
    for room in rooms['rooms']:
        for i,image in enumerate(room['image_sources'][3:],start=3):
            url=canonical(image['source_url'])
            if url in seen:
                raise ValueError('Duplicate original room image URL: '+url)
            seen.add(url)
            result.append({
                'cms_slug':room['slug'],'title':room['title'],
                'source_page_url':room['source_url'],
                'source_image_url':image['source_url'],
                'source_image_index':i,'original_url':url,
                'source_alt':image.get('alt',''),
                'source_snapshot':'official-exposition-rooms.json',
                'source_html_sha256':room['html_sha256'],
            })
    # Finish the two ORIGINAL four-photo program galleries, preserving the
    # source-bounded 3-photo queue and all prior manifest associations.
    for filename,key in SOURCES:
        programs=json.loads((SRC/filename).read_text(encoding='utf-8'))[key]
        for entry in programs:
            for i,image in enumerate(entry.get('image_links',[])[3:],start=3):
                url=canonical(image['url'])
                if url in seen:raise ValueError('Duplicate genuine gallery URL: '+url)
                seen.add(url)
                result.append({
                    'cms_slug':entry.get('slug') or entry.get('cms_slug'),
                    'title':entry['title'],'source_page_url':entry['source_url'],
                    'source_image_url':image['url'],'source_image_index':i,
                    'original_url':url,'source_alt':image.get('alt',''),
                    'source_snapshot':filename,
                    'source_html_sha256':entry.get('html_sha256'),
                })
    # Eight remaining genuine images in each real exhibition archive index.
    for exhibition_index in indices['indexes']:
        if exhibition_index['slug'] not in ('exhibitions-past','exhibitions-virtual'):
            continue
        for i,photo in enumerate(exhibition_index['image_links'][4:],start=4):
            url=canonical(photo['url'])
            if url in seen:raise ValueError('Duplicate museum archive URL: '+url)
            seen.add(url)
            result.append({
                'cms_slug':exhibition_index['slug'],
                'title':exhibition_index['title'],
                'source_page_url':exhibition_index['source_url'],
                'source_image_url':photo['url'],'source_image_index':i,
                'original_url':url,'source_alt':photo.get('alt',''),
                'source_snapshot':'official-exhibition-indexes.json',
                'source_html_sha256':exhibition_index['html_sha256'],
            })
    # Standalone original overview gallery belongs to an existing private
    # museum page, not to a fictitious individual excursion.
    overview_pages=json.loads((SRC/'official-excursion-pages.json').read_text(encoding='utf-8'))
    if overview_pages.get('source')!=HOST:raise ValueError('Unknown overview original')
    overview=[x for x in overview_pages['pages'] if x['path']=='/obzornaya-ekskursiya']
    if len(overview)!=1:raise ValueError('Original overview excursion missing')
    overview=overview[0]
    for i,photo in enumerate(overview['image_links']):
        url=canonical(photo['url'])
        if url in seen:raise ValueError('Duplicate museum overview URL: '+url)
        seen.add(url)
        result.append({
            'cms_slug':'excursion-overview',
            'title':overview['title'],'source_page_url':overview['source_url'],
            'source_image_url':photo['url'],'source_image_index':i,
            'original_url':url,'source_alt':photo.get('alt',''),
            'source_snapshot':'official-excursion-pages.json',
            'source_html_sha256':overview['html_sha256'],
        })
    return result

def detect(buf:bytes)->str:
    if buf.startswith(b'\xff\xd8\xff') and buf[-2:]==b'\xff\xd9':return 'jpg'
    if buf.startswith(b'\x89PNG\r\n\x1a\n') and b'IEND' in buf[-30:]:return 'png'
    if buf.startswith(b'RIFF') and buf[8:12]==b'WEBP':return 'webp'
    raise ValueError('Image bytes are not allowed JPEG PNG or WebP')

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--limit',type=int,default=24)
    ap.add_argument('--delay',type=float,default=10.0)
    args=ap.parse_args()
    if args.delay<10:raise ValueError('Source robots crawl delay >= 10 seconds')
    candidates=queue()
    if not 1<=args.limit<=len(candidates):raise ValueError('Invalid limit')
    OUT.mkdir(parents=True,exist_ok=True)
    previous={}
    if MANIFEST.exists():
        prior=json.loads(MANIFEST.read_text())
        if prior.get('source')!=HOST:raise ValueError('Untrusted existing manifest')
        previous={r['original_url']:r for r in prior.get('files',[])}
    saved=[];errors=[];last_fetch=None
    for i,item in enumerate(candidates[:args.limit]):
        url=item['original_url']
        if url in previous:
            old=previous[url]
            file=OUT/old['local_name']
            if file.is_file() and file.stat().st_size==old['size_bytes'] and sha256(file.read_bytes()).hexdigest()==old['sha256']:
                saved.append(old); print('CACHED',i+1,item['cms_slug'],flush=True);continue
        if last_fetch is not None:
            sleep(max(0,args.delay-(monotonic()-last_fetch)))
        last_fetch=monotonic()
        try:
            with urlopen(Request(url,headers={
                'User-Agent':'Mozilla/5.0 (MusBread original museum photo preservation)',
                'Accept':'image/jpeg,image/png,image/webp'}),timeout=40) as response:
                if response.status!=200:raise ValueError('Source not HTTP 200')
                content_type=response.headers.get('Content-Type','')
                raw=response.read(MAX_SIZE+1)
                if len(raw)>MAX_SIZE or len(raw)<250:
                    raise ValueError('Image unexpectedly small or too large')
                if response.headers.get('Content-Length') and int(response.headers['Content-Length'])!=len(raw):
                    raise ValueError('Truncated original photo')
            fmt=detect(raw)
            if 'image/' not in content_type.lower():
                raise ValueError('Source not image Content-Type')
            digest=sha256(raw).hexdigest()
            local=OUT/(digest+'.'+fmt)
            if local.exists():
                if local.read_bytes()!=raw:raise ValueError('Original local digest mismatch')
            else:
                local.write_bytes(raw)
            saved.append({**item,'sha256':digest,'local_name':local.name,
                          'size_bytes':len(raw),'format':fmt,'content_type':content_type})
            print('OK',i+1,'/',args.limit,item['cms_slug'],len(raw),'bytes',flush=True)
        except Exception as e:
            errors.append({'url':url,'cms_slug':item['cms_slug'],'error':type(e).__name__})
            print('SKIPPED',i+1,item['cms_slug'],type(e).__name__,flush=True)
    if len(saved)<max(5,args.limit//2):
        raise RuntimeError('Insufficient actual verified museum photo sources; refuse to replace manifest')
    payload={'source':HOST,'captured_utc':datetime.now(timezone.utc).isoformat(timespec='seconds'),
             'candidate_count':len(candidates),'limit':args.limit,
             'count':len(saved),'rights_status':'not-verified-private-only',
             'files':saved,'errors':errors}
    tmp=MANIFEST.with_suffix('.json.tmp')
    tmp.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    tmp.replace(MANIFEST)
    print('ORIGINAL PHOTOS ARCHIVED',len(saved),'/',args.limit,
          'source-verified; private no public rights',flush=True)
if __name__=='__main__':main()
