#!/usr/bin/env python3
"""Self-contained static Next.js museum photo export from ORIGINAL MAC MINI bytes.

Do not crawl or hotlink the retiring site: only read SHA-256-verified, private
museum originals already preserved on ArvectumSSD. Export the original contents
as full-frame display-optimized WebP files and a source-URL lookup manifest.
The museum's former DNS/Drupal/file paths are never used to fetch an image in
our rendered site; old URLs are provenance metadata only.
"""
from __future__ import annotations
import argparse,hashlib,json,os,re,sys
from io import BytesIO
from pathlib import Path
from urllib.parse import urlparse
from PIL import Image,ImageOps

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'.local_archive/museum-official-photos'
MANIFEST=SOURCE/'manifest.json'
PUBLIC=ROOT/'apps/web/public/media/museum-source'
INDEX=ROOT/'apps/web/src/data/official-museum-photo-assets.json'
SOURCE_HOST='https://muzei-xleb.ru'
DEFAULT_MAX_EDGE=1920

def canonical(url:str)->str:
    u=urlparse(url)
    if u.scheme!='https' or u.netloc!='muzei-xleb.ru' or not u.path.startswith('/sites/default/files/'):
        raise ValueError('Only verified original museum photo source allowed')
    path=re.sub(r'^/sites/default/files/styles/[^/]+/public/', '/sites/default/files/',u.path)
    if not re.search(r'\.(jpe?g|png|webp)$',path,re.I):
        raise ValueError('Invalid published museum raster image path')
    return SOURCE_HOST+path

def generate(max_edge:int=DEFAULT_MAX_EDGE,verify_only:bool=False)->dict:
    if not 700<=max_edge<=2400:raise ValueError('Invalid static museum photo display dimension')
    m=json.loads(MANIFEST.read_text(encoding='utf-8'))
    if m.get('source')!=SOURCE_HOST or m.get('count')!=len(m.get('files',[])) or m.get('errors') or m.get('count',0)<208:
        raise RuntimeError('Original official museum source archive not complete/verified')
    # Validate the accepted set against actual captured museum page references,
    # not an arbitrary input file with a familiar-looking source domain.
    sys.path.insert(0,str(ROOT/'scripts'))
    from cache_official_museum_photos import queue
    expected=queue()
    accepted={r['original_url']:(r['cms_slug'],r['source_image_url']) for r in expected}
    if len(accepted)!=len(expected) or len(accepted)!=len(m['files']):
        raise RuntimeError('Photo manifest is not aligned to actual official source records')
    photos={};assets={};asset_bytes=0
    for item in m['files']:
        original=item['original_url']; styled=item['source_image_url']
        if (item['cms_slug'],styled)!=accepted.get(original):
            raise RuntimeError('Museum original photo not supported by captured page data: '+original)
        if canonical(styled)!=original:raise RuntimeError('Unsafe styled image URL: '+styled)
        name=item['local_name'];digest=item['sha256']
        if not re.fullmatch(r'[0-9a-f]{64}',digest) or not re.fullmatch(r'[0-9a-f]{64}\.(jpg|png|webp)',name) or not name.startswith(digest):
            raise RuntimeError('Unverified original file identity')
        path=SOURCE/name
        if not path.is_file() or path.stat().st_size!=item['size_bytes'] or hashlib.sha256(path.read_bytes()).hexdigest()!=digest:
            raise RuntimeError('Museum original bytes missing or altered: '+name)
        if digest not in assets:
            webp_name=digest+'.webp'
            dest=PUBLIC/webp_name
            if not verify_only:
                PUBLIC.mkdir(parents=True,exist_ok=True)
                with Image.open(path) as original_image:
                    im=ImageOps.exif_transpose(original_image)
                    if im.mode not in ('RGB','RGBA'):
                        im=im.convert('RGBA' if 'A' in im.getbands() else 'RGB')
                    # Never crop, watermark or invent missing source pixels.
                    im.thumbnail((max_edge,max_edge),Image.Resampling.LANCZOS)
                    if im.width<1 or im.height<1:raise RuntimeError('Invalid source frame')
                    tmp=dest.with_suffix('.webp.tmp')
                    im.save(tmp,format='WEBP',quality=84,method=5)
                tmp.replace(dest)
            if not dest.is_file() or dest.stat().st_size<250:
                raise RuntimeError('Original museum photo not included in static site: '+webp_name)
            raw=dest.read_bytes()
            with Image.open(BytesIO(raw)) as saved:
                if saved.format!='WEBP' or saved.width<1 or saved.height<1:
                    raise RuntimeError('Invalid museum export asset '+webp_name)
                dimension=[saved.width,saved.height]
            assets[digest]={
                'path':'/media/museum-source/'+webp_name,
                'original_sha256':digest,
                'static_sha256':hashlib.sha256(raw).hexdigest(),
                'bytes':len(raw),'width':dimension[0],'height':dimension[1],
            }
            asset_bytes+=len(raw)
        if original in photos:raise RuntimeError('Duplicate original museum page URL: '+original)
        photos[original]={
            **assets[digest],
            'original_url':original,
            'source_image_url':styled,
            'source_page_url':item['source_page_url'],
            'source_slug':item['cms_slug'],
        }
    if not verify_only:
        output={'source':SOURCE_HOST,'mode':'self-hosted-static-images',
                'description':'Museum original URLs are provenance only; every image bytes and URL served by new static site, independent of retiring Drupal.',
                'count':len(photos),'unique_static_assets':len(assets),
                'max_edge_px':max_edge,'total_static_bytes':asset_bytes,
                'photos':photos}
        INDEX.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    else:
        saved=json.loads(INDEX.read_text(encoding='utf-8'))
        if saved.get('count')!=len(photos) or saved.get('unique_static_assets')!=len(assets) or saved['photos']!=photos:
            raise RuntimeError('Static media mapping stale or not identical to exported bytes')
    print('SELF_HOSTED_MUSEUM_PHOTOS',len(photos),'original museum URLs',len(assets),'unique static assets',f'{asset_bytes/1048576:.2f} MiB','verified' if verify_only else 'exported',flush=True)
    return {'count':len(photos),'unique':len(assets),'bytes':asset_bytes}

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--verify-only',action='store_true')
    p.add_argument('--max-edge',type=int,default=DEFAULT_MAX_EDGE)
    args=p.parse_args()
    generate(args.max_edge,args.verify_only)
