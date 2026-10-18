#!/usr/bin/env python3
"""Preserve 37 actual museum JPG/JPEG links in the original /novosti HTML.

Save originals privately, self-host genuine WebP in static site, verify
literal original links against SHA-256 protected source HTML. Respect 10s crawl delay.
"""
from __future__ import annotations
import argparse,csv,hashlib,json,re,time
from pathlib import Path
from urllib.parse import urljoin,urlsplit
from urllib.request import Request,urlopen
from urllib.error import HTTPError
from lxml import html
from PIL import Image,ImageOps
ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'apps/web/src/data'
CSV=ROOT/'docs/seo/DEEP_IMAGE_ORIGINAL_SOURCE_URLS_20261018.csv'
PRIVATE=ROOT/'.local_archive/deep-original-images'
PUBLIC=ROOT/'apps/web/public/media/museum-source'
OUTPUT=SRC/'official-deep-news-image-assets.json'
HOST='https://muzei-xleb.ru'

def verified_urls():
 with CSV.open(encoding='utf-8-sig',newline='') as f: rows=list(csv.DictReader(f,delimiter=';'))
 paths={x['linked_path'] for x in rows if x['gap_type']=='UNCOVERED_ORIGINAL_MUSEUM_IMAGE'}
 if len(paths)!=37:raise RuntimeError('Changed original deep image source manifest')
 d=json.loads((SRC/'official-museum-crosslink-pages.json').read_text(encoding='utf-8'))
 if d['source']!=HOST:raise RuntimeError('Untrusted original museum content source')
 originals={}
 for record in d['pages']:
  if record['source_url']!='https://muzei-xleb.ru/novosti':continue
  body=record['html']
  if hashlib.sha256(body.encode()).hexdigest()!=record['html_sha256']:raise RuntimeError('Museum news content source SHA mismatch')
  for link in html.fragment_fromstring(body,create_parent='div').xpath('.//a[@href]'):
   u=urlsplit(urljoin(record['source_url'],link.get('href','')))
   if u.netloc=='muzei-xleb.ru' and u.path in paths:
    originals[u.path]={'original_url':HOST+u.path,'source_page_url':record['source_url'],
       'source_html_sha256':record['html_sha256'],'source_label':' '.join(link.text_content().split())[:120]}
 if set(originals)!=paths:raise RuntimeError('One or more original museum image references unverified '+str(paths-set(originals)))
 return originals

def run(limit:int=37,delay:float=10.0,verify_only:bool=False):
 if not 1<=limit<=37 or delay<10:raise ValueError('Original museum 10s crawl delay and source bound limit required')
 refs=verified_urls();PRIVATE.mkdir(parents=True,exist_ok=True);PUBLIC.mkdir(parents=True,exist_ok=True)
 prior=json.loads(OUTPUT.read_text(encoding='utf-8')) if OUTPUT.is_file() else {'source':HOST,'photos':{},'unavailable':[]}
 if prior.get('source')!=HOST:raise RuntimeError('Unexpected original museum extra photo mapping')
 mapping=dict(prior['photos']);unavailable={x['original_url']:x for x in prior.get('unavailable',[])}
 last_fetch=False
 for i,(path,record) in enumerate(sorted(refs.items())[:limit],start=1):
  url=record['original_url'];stored=mapping.get(url)
  if stored:
   original=PRIVATE/(stored['original_sha256']+'.'+stored['original_format'])
   thumb=PUBLIC/stored['path'].removeprefix('/') .replace('media/museum-source/','')
   if original.is_file() and thumb.is_file() and original.stat().st_size==stored['original_bytes'] and hashlib.sha256(original.read_bytes()).hexdigest()==stored['original_sha256'] and hashlib.sha256(thumb.read_bytes()).hexdigest()==stored['static_sha256']:
    print('CACHED_ORIGINAL_SOURCE_IMAGE',i,limit,path,flush=True);continue
   raise RuntimeError('Original museum cached source image modified unexpectedly '+url)
  if url in unavailable:
   print('ORIGINAL_IMAGE_ALREADY_UNAVAILABLE',i,limit,url,unavailable[url]['http_status'],flush=True)
   continue
  if verify_only:raise RuntimeError('Missing original source photo '+url)
  if last_fetch:time.sleep(delay)
  last_fetch=True
  try:
   with urlopen(Request(url,headers={'User-Agent':'Mozilla/5.0 (MusBread museum source-only photo archive)','Accept':'image/jpeg,image/png,image/webp'}),timeout=40) as resp:
    if resp.status!=200 or not resp.headers.get('Content-Type','').lower().startswith('image/'):
     raise RuntimeError('Old museum image not real image HTTP 200 '+url)
    raw=resp.read(14_000_001)
  except HTTPError as e:
   if e.code not in (403,404,410):raise
   unavailable[url]={**record,'http_status':e.code}
   print('MUSEUM_ORIGINAL_IMAGE_UNAVAILABLE',i,limit,e.code,url,flush=True)
   OUTPUT.write_text(json.dumps({'source':HOST,'count':len(mapping),'photos':mapping,'unavailable':list(unavailable.values())},ensure_ascii=False,indent=2)+'\n')
   continue
  if not 300<len(raw)<=14_000_000:raise RuntimeError('Original museum image invalid byte length '+url)
  if raw.startswith(b'\xff\xd8\xff') and raw.endswith(b'\xff\xd9'):ext='jpg'
  elif raw.startswith(b'\x89PNG\r\n\x1a\n') and b'IEND' in raw[-40:]:ext='png'
  elif raw.startswith(b'RIFF') and raw[8:12]==b'WEBP':ext='webp'
  else:raise RuntimeError('Original museum image file magic not permitted '+url)
  digest=hashlib.sha256(raw).hexdigest();original=PRIVATE/(digest+'.'+ext);original.write_bytes(raw)
  webp=PUBLIC/(digest+'.webp')
  if not webp.is_file():
   with Image.open(original) as opened:
    im=ImageOps.exif_transpose(opened)
    if im.mode not in ('RGB','RGBA'):im=im.convert('RGB')
    im.thumbnail((1920,1920),Image.Resampling.LANCZOS)
    im.save(webp,format='WEBP',quality=84,method=5)
  if webp.stat().st_size<250:raise RuntimeError('Museum WebP export empty '+url)
  mapping[url]={**record,'original_sha256':digest,'original_format':ext,'original_bytes':len(raw),
    'path':'/media/museum-source/'+webp.name,'static_sha256':hashlib.sha256(webp.read_bytes()).hexdigest()}
  OUTPUT.write_text(json.dumps({'source':HOST,'count':len(mapping),'photos':mapping,'unavailable':list(unavailable.values())},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
  print('COPIED_REAL_MUSEUM_NEWS_IMAGE',i,limit,url,len(raw),flush=True)
 if verify_only and (len(mapping)+len(unavailable)!=37):raise RuntimeError('Not all source links resolved')
 print('MUSEUM_DEEP_IMAGES_DONE',len(mapping),'self_hosted',len(unavailable),'unavailable_source',flush=True)
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--limit',type=int,default=37);a.add_argument('--delay',type=float,default=10);a.add_argument('--verify-only',action='store_true');args=a.parse_args();run(args.limit,args.delay,args.verify_only)
