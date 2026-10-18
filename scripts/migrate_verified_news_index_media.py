#!/usr/bin/env python3
"""Copy actual JPEGs linked by the ORIGINAL /novosty listing; never hotlink.

Source URL is authorized solely by exact literal anchors in the museum page
already downloaded and SHA-verified on Mac mini. Public path is a real WebP.
"""
from __future__ import annotations
import argparse,hashlib,json,re,time
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import Request,urlopen
from PIL import Image,ImageOps
ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'apps/web/src/data/official-remaining-original-sections.json'
PRIVATE=ROOT/'.local_archive/museum-news-index-original-images'
PUBLIC=ROOT/'apps/web/public/media/museum-source'
OUT=ROOT/'apps/web/src/data/official-news-index-photo-assets.json'
HOST='https://muzei-xleb.ru'

def originals():
 d=json.loads(SRC.read_text(encoding='utf-8'))
 if d.get('source')!=HOST:raise RuntimeError('Not original museum index corpus')
 pages=[x for x in d['pages'] if x['path']=='/novosty']
 if len(pages)!=1 or not re.fullmatch(r'[a-f0-9]{64}',pages[0]['source_page_sha256']):
  raise RuntimeError('Original first news page not SHA-verified')
 x=pages[0]
 verified=(ROOT/'.local_archive/remaining-museum-original-section-html/novosty.html').read_bytes()
 if hashlib.sha256(verified).hexdigest()!=x['source_page_sha256']:
  raise RuntimeError('Original museum /novosty source listing changed')
 seen=set();urls=[]
 for a in x['source_links']:
  href=a['href'];u=urlsplit(href)
  if u.scheme=='https' and u.netloc=='muzei-xleb.ru' and u.path.startswith('/sites/default/files/') and re.search(r'\.(jpe?g|png|webp)$',u.path,re.I):
   key=HOST+u.path
   if key not in seen:urls.append(key);seen.add(key)
 if len(urls)!=10:raise RuntimeError('Original museum first listing has unexpected original image links count '+str(len(urls)))
 return x,urls

def go(*,verify_only=False):
 page,urls=originals()
 if not verify_only:PRIVATE.mkdir(parents=True,exist_ok=True);PUBLIC.mkdir(parents=True,exist_ok=True)
 prior=json.loads(OUT.read_text()) if OUT.exists() else None
 if verify_only and (not prior or prior.get('count')!=10):
  raise RuntimeError('Original news first-page images missing from static manifest')
 mapping={};last_fetch=False
 for i,url in enumerate(urls):
  stored=prior['photos'].get(url) if prior else None
  if stored:
   name=stored['original_sha256']+'.'+stored['original_format']
   original=PRIVATE/name
   if not original.is_file() or hashlib.sha256(original.read_bytes()).hexdigest()!=stored['original_sha256']:
    stored=None
  if not stored and verify_only:raise RuntimeError('Original museum photo missing '+url)
  if not stored:
   if last_fetch:time.sleep(10)
   with urlopen(Request(url,headers={'User-Agent':'Mozilla/5.0 (MuseumBread source photo preservation)','Accept':'image/jpeg,image/png,image/webp'}),timeout=36) as response:
    if response.status!=200 or not response.headers.get('Content-Type','').startswith('image/'):
     raise RuntimeError('Original museum linked image not HTTP image '+url)
    raw=response.read(12_000_001)
   last_fetch=True
   if not 300<=len(raw)<=12_000_000:raise RuntimeError('Original photo invalid byte length '+url)
   if raw.startswith(b'\xff\xd8\xff'):fmt='jpg'
   elif raw.startswith(b'\x89PNG\r\n\x1a\n'):fmt='png'
   elif raw.startswith(b'RIFF') and raw[8:12]==b'WEBP':fmt='webp'
   else:raise RuntimeError('Original image magic invalid '+url)
   sha=hashlib.sha256(raw).hexdigest()
   (PRIVATE/(sha+'.'+fmt)).write_bytes(raw)
   stored={'original_sha256':sha,'original_format':fmt,'source_url':url,'original_bytes':len(raw)}
  raw=(PRIVATE/(stored['original_sha256']+'.'+stored['original_format'])).read_bytes()
  webp=PUBLIC/(stored['original_sha256']+'.webp')
  if not verify_only and not webp.is_file():
   with Image.open(PRIVATE/(stored['original_sha256']+'.'+stored['original_format'])) as src:
    image=ImageOps.exif_transpose(src)
    if image.mode not in ('RGB','RGBA'):image=image.convert('RGB')
    image.thumbnail((1920,1920),Image.Resampling.LANCZOS)
    image.save(webp,format='WEBP',quality=84,method=5)
  if not webp.is_file() or webp.stat().st_size<250:
   raise RuntimeError('Original museum news WebP not exported '+url)
  static_sha=hashlib.sha256(webp.read_bytes()).hexdigest()
  if verify_only and stored['static_sha256']!=static_sha:raise RuntimeError('Museum index WebP checksum mismatched')
  mapping[url]={**stored,'path':'/media/museum-source/'+webp.name,
    'static_sha256':static_sha,'source_page_url':page['source_url'],
    'source_page_sha256':page['source_page_sha256']}
  print(('VERIFIED' if verify_only else 'MIGRATED')+'_REAL_MUSEUM_NEWS_INDEX_PHOTO',i+1,len(urls),url,flush=True)
 result={'source':HOST,'count':len(mapping),'photos':mapping}
 if not verify_only:OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 elif result!=prior:raise RuntimeError('Museum source-image mapping changed during source byte validation')
 print('NEWS_INDEX_IMAGES_SELF_HOSTED',len(mapping),'source linked JPG originals',flush=True)
 return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--verify-only',action='store_true');args=p.parse_args();go(verify_only=args.verify_only)
