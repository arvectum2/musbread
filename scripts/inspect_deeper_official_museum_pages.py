#!/usr/bin/env python3
"""Direct, slow original-site audit of 21 actual deep links in museum HTML.

Authoritative source URLs and referrer HTML SHA are verified before HTTP. All
cached originals remain privately on ArvectumSSD; no GUI or external browsers.
"""
from __future__ import annotations
import csv,hashlib,json,time
from pathlib import Path
from urllib.parse import urljoin,urlsplit
from urllib.request import Request,urlopen
from urllib.error import HTTPError
from lxml import html
ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'apps/web/src/data'
CSV=ROOT/'docs/seo/DEEP_PAGE_ORIGINAL_SOURCE_URLS_20261018.csv'
PRIVATE=ROOT/'.local_archive/deep-original-museum-pages'
HOST='https://muzei-xleb.ru'
CORPUS=[('official-museum-news.json','articles'),('official-museum-news-archive.json','articles'),('official-exhibition-details.json','exhibitions'),('official-exhibition-archive.json','exhibitions'),('official-exhibition-news-linked.json','exhibitions'),('official-node-linked-exhibitions.json','exhibitions'),('official-excursion-programs.json','programs'),('official-workshop-pages.json','programs'),('official-exposition-rooms.json','rooms'),('official-original-legacy-sections.json','sections'),('official-museum-crosslink-pages.json','pages')]
def originals():
 with CSV.open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f,delimiter=';'))
 paths={x['linked_path'] for x in rows if x['gap_type']=='UNCOVERED_ORIGINAL_MUSEUM_PAGE'}
 if len(paths)!=21:raise RuntimeError('21 source-proven museum crosslinks changed')
 valid={}
 for name,key in CORPUS:
  d=json.loads((DATA/name).read_text(encoding='utf-8'))
  if d['source']!=HOST:raise RuntimeError('Incorrect museum source '+name)
  for entry in d[key]:
   body=entry['html'];sha=hashlib.sha256(body.encode()).hexdigest()
   if sha!=entry['html_sha256']:raise RuntimeError('Altered original museum referrer text '+entry['source_url'])
   for link in html.fragment_fromstring(body,create_parent='div').xpath('.//a[@href]'):
    u=urlsplit(urljoin(entry['source_url'],link.get('href','')))
    if u.hostname=='muzei-xleb.ru' and u.path in paths:
     valid.setdefault(u.path,{'path':u.path,'original_source_url':HOST+u.path,
       'original_referrer':entry['source_url'],'original_referrer_sha256':sha})
 if set(valid)!=paths:raise RuntimeError('Museum deep-page sources unverified '+str(paths-set(valid)))
 return valid

def fetch():
 verified=originals();PRIVATE.mkdir(parents=True,exist_ok=True)
 manifest=PRIVATE/'manifest.json'
 old=json.loads(manifest.read_text()) if manifest.exists() else {'source':HOST,'pages':[]}
 if old['source']!=HOST:raise RuntimeError('Bad museum private source archive')
 done={r['path']:r for r in old['pages']};last_fetch=False
 for path,item in sorted(verified.items()):
  if path in done:
   if done[path]['status']==200:
    original=PRIVATE/(path.lstrip('/').replace('/','__')+'.html')
    if not original.is_file() or hashlib.sha256(original.read_bytes()).hexdigest()!=done[path]['source_html_sha256']:
     raise RuntimeError('Previously verified museum source disappeared '+path)
   print('CACHED_VERIFIED_OLD_MUSEUM_PAGE',path,done[path]['status'],flush=True);continue
  if last_fetch:time.sleep(10)
  last_fetch=True
  try:
   with urlopen(Request(HOST+path,headers={'User-Agent':'Mozilla/5.0 (MuseumBread source-preservation old URL audit)','Accept':'text/html'}),timeout=40) as resp:
    raw=resp.read(2_000_001);status=resp.status;final=resp.geturl();ctype=resp.headers.get('Content-Type','')
   if status!=200 or len(raw)>2_000_000 or not ctype.lower().startswith('text/html'):
    raise RuntimeError('Unexpected source response type/status '+path+' '+ctype)
   resolved=urlsplit(final)
   if resolved.scheme!='https' or resolved.netloc!='muzei-xleb.ru':
    raise RuntimeError('Museum original source unexpectedly redirects off museum domain '+final)
   tree=html.fromstring(raw)
   heads=tree.xpath('//h1')
   title=' '.join(heads[0].text_content().split()) if len(heads)==1 else ''
   record={**item,'status':200,'effective_url':final,'source_html_sha256':hashlib.sha256(raw).hexdigest(),
     'title':title,'response_bytes':len(raw),'content_type':ctype}
   (PRIVATE/(path.lstrip('/').replace('/','__')+'.html')).write_bytes(raw)
  except HTTPError as e:
   record={**item,'status':e.code,'effective_url':e.geturl(),'source_html_sha256':'',
     'title':'','response_bytes':0,'content_type':''}
  done[path]=record
  manifest.write_text(json.dumps({'source':HOST,'count':len(done),'pages':list(done.values())},ensure_ascii=False,indent=2)+'\n')
  print('VERIFIED_ACTUAL_OLD_MUSEUM_DEEP_PAGE',path,'HTTP',record['status'],'LOCATION',record['effective_url'],'H1',record['title'][:65],flush=True)
 print('DEEP_MUSEUM_SOURCE_PAGE_CHECKED',len(done),'of',len(verified),flush=True)
if __name__=='__main__':fetch()
