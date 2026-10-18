#!/usr/bin/env python3
"""Preserve genuine DOCX/PDF linked inside original museum legal/content pages.

Never invent old missing files. Source hyperlinks must be present in genuine,
SHA-verified museum HTML and identical to the saved uncovered-links audit.
"""
from __future__ import annotations
import argparse,csv,hashlib,json,time
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.error import HTTPError
from urllib.parse import urlsplit,urljoin
from lxml import html
ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'apps/web/src/data'
CSV=ROOT/'docs/seo/DEEP_DOCUMENT_ORIGINAL_SOURCE_URLS_20261018.csv'
OUT=ROOT/'.local_archive/deep-original-documents'
HOST='https://muzei-xleb.ru'
AUTH=[('official-museum-news.json','articles'),('official-museum-news-archive.json','articles'),('official-exhibition-details.json','exhibitions'),('official-exhibition-archive.json','exhibitions'),('official-exhibition-news-linked.json','exhibitions'),('official-node-linked-exhibitions.json','exhibitions'),('official-excursion-programs.json','programs'),('official-workshop-pages.json','programs'),('official-exposition-rooms.json','rooms'),('official-original-legacy-sections.json','sections'),('official-museum-crosslink-pages.json','pages')]
def signed_docs():
 with CSV.open(encoding='utf-8-sig',newline='') as f:links=list(csv.DictReader(f,delimiter=';'))
 missing={x['linked_path'] for x in links if x['gap_type']=='UNCOVERED_ORIGINAL_MUSEUM_DOCUMENT'}
 if len(missing)!=24:raise RuntimeError('Additional original museum legal documents source corpus changed')
 auth={}
 for name,key in AUTH:
  d=json.loads((SRC/name).read_text(encoding='utf-8'))
  for article in d[key]:
   src=article['source_url'];body=article['html']
   if hashlib.sha256(body.encode()).hexdigest()!=article['html_sha256']:
    raise RuntimeError('Authentic museum document referrer source SHA mismatch '+src)
   for a in html.fragment_fromstring(body,create_parent='div').xpath('.//a[@href]'):
    url=urlsplit(urljoin(src,a.get('href','')))
    if url.netloc=='muzei-xleb.ru' and url.path in missing:
     auth.setdefault(url.path,{'url':HOST+url.path,'referrer':src,'label':' '.join(a.text_content().split())[:120]})
 if set(auth)!=missing:raise RuntimeError('Unverified old linked PDF or DOCX '+str(missing-set(auth)))
 return auth

def main(limit:int=24,delay:int=10):
 if not 10<=delay or not 1<=limit<=24:raise ValueError('Respect original museum crawl-delay and batch limit')
 docs=signed_docs();OUT.mkdir(parents=True,exist_ok=True)
 manifest=OUT/'manifest.json';missing_file=OUT/'unavailable.json'
 old=json.loads(manifest.read_text()) if manifest.exists() else {'source':HOST,'files':[]}
 if old.get('source')!=HOST:raise RuntimeError('Unexpected local museum document archive')
 ok={x['url']:x for x in old['files']}
 bad={x['url']:x for x in json.loads(missing_file.read_text())['files']} if missing_file.exists() else {}
 last_request=False
 for i,(path,info) in enumerate(sorted(docs.items(),reverse=True)[:limit],1):
  url=info['url'];current=ok.get(url)
  if current:
   f=OUT/current['local_name']
   if f.is_file() and f.stat().st_size==current['size_bytes'] and hashlib.sha256(f.read_bytes()).hexdigest()==current['sha256']:
    print('PRESERVED_CACHED_ORIGINAL',i,limit,url,flush=True);continue
  if url in bad:
   print('PRESERVED_OLD_HTTP_UNAVAILABLE',i,limit,url,bad[url]['http_status'],flush=True);continue
  if last_request:time.sleep(delay)
  last_request=True
  try:
   with urlopen(Request(url,headers={'User-Agent':'Mozilla/5.0 (MuseumBread original document migration)','Accept':'application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document'}),timeout=55) as resp:
    if resp.status!=200:raise RuntimeError('Unverified original museum public file HTTP status')
    raw=resp.read(80_000_001)
  except HTTPError as e:
   if e.code not in (403,404,410):raise
   bad[url]={**info,'http_status':e.code}
   print('UNAVAILABLE_AT_ORIGINAL_MUSEUM',i,limit,e.code,url,flush=True)
   missing_file.write_text(json.dumps({'source':HOST,'count':len(bad),'files':list(bad.values())},ensure_ascii=False,indent=2)+'\n')
   continue
  extension=Path(path).suffix.lower()
  if not 200<len(raw)<=80_000_000 or not (extension=='.pdf' and raw.startswith(b'%PDF') or extension=='.docx' and raw.startswith(b'PK')):
   raise RuntimeError('Museum original downloaded file content invalid '+url)
  sha=hashlib.sha256(raw).hexdigest();name=sha+extension
  (OUT/name).write_bytes(raw)
  ok[url]={**info,'sha256':sha,'size_bytes':len(raw),'local_name':name}
  manifest.write_text(json.dumps({'source':HOST,'count':len(ok),'files':list(ok.values()),'errors':[]},ensure_ascii=False,indent=2)+'\n')
  print('DOWNLOADED_ORIGINAL_MUSEUM_DEEP_DOCUMENT',i,limit,url,len(raw),flush=True)
 print('SOURCE_VERIFIED_MUSEUM_DEEP_DOCUMENTS',len(ok),'downloaded',len(bad),'unavailable from original',flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--limit',type=int,default=24);p.add_argument('--delay',type=int,default=10);a=p.parse_args();main(a.limit,a.delay)
