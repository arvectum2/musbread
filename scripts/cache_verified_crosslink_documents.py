#!/usr/bin/env python3
"""Preserve source-proven additional museum docs linked in existing original HTML.
Only exact public URLs in SHA-verified original source bodies are eligible.
Existing old 404 historical PDF is logged, NEVER substituted.
"""
from __future__ import annotations
import csv,hashlib,json,re,time
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.error import HTTPError
from lxml import html
from urllib.parse import urlsplit,urljoin
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'apps/web/src/data'
OUT=ROOT/'.local_archive/extra-original-documents'
CSV=ROOT/'docs/seo/ORIGINAL_MUSEUM_CROSSLINK_GAPS_20261018.csv'
HOST='https://muzei-xleb.ru'
SOURCES=[('official-museum-news.json','articles'),('official-museum-news-archive.json','articles'),('official-exhibition-details.json','exhibitions'),('official-exhibition-archive.json','exhibitions'),('official-exhibition-news-linked.json','exhibitions'),('official-node-linked-exhibitions.json','exhibitions'),('official-excursion-programs.json','programs'),('official-workshop-pages.json','programs'),('official-exposition-rooms.json','rooms'),('official-original-legacy-sections.json','sections'),('official-excursion-pages.json','pages')]
def proven():
  # This immutable validated batch was proven by actual source HTML when
  # the crosslink crawl first discovered the files. A NEW crosslink audit
  # may now find dozens more missing documents; that must NOT silently mutate
  # this source-locked historical import set. Expand using a new batch.
  paths={
    '/sites/default/files/page/202110271242-prikaz_no94.pdf',
    '/sites/default/files/page/20240419153512-prikaz_pravila_poseshcheniya_organizovannymi_gruppami_ekskursiy.pdf',
    '/sites/default/files/page/20251203120738-informaciya_dlya_dariteley.docx',
  }
  documents={}
  for fname,key in SOURCES:
    d=json.loads((BASE/fname).read_text(encoding='utf-8'))
    for a in d[key]:
      body=a['html']
      if hashlib.sha256(body.encode()).hexdigest()!=a['html_sha256']:
        raise RuntimeError('Altered museum source HTML '+a['source_url'])
      links=[urlsplit(urljoin(a['source_url'],x.get('href',''))) for x in html.fragment_fromstring(body,create_parent='div').xpath('.//a[@href]')]
      for u in links:
        if u.hostname=='muzei-xleb.ru' and u.path in paths:
          if u.path.endswith('.pdf') or u.path.endswith('.docx'):
            documents.setdefault(u.path,{'url':HOST+u.path,'referer':a['source_url']})
  if set(documents)!=paths:raise RuntimeError('Unproven original museum linked file sources '+str(paths-set(documents)))
  return documents

def run():
  originals=proven();OUT.mkdir(parents=True,exist_ok=True)
  prior=json.loads((OUT/'manifest.json').read_text()) if (OUT/'manifest.json').exists() else None
  known={x['url']:x for x in (prior['files'] if prior else [])}
  saved=[];unavailable=[];was_fetched=False
  for i,(path,record) in enumerate(sorted(originals.items()),1):
    url=record['url'];current=known.get(url)
    if current:
      name=OUT/current['local_name'];ok=(name.is_file() and name.stat().st_size==current['size_bytes'] and hashlib.sha256(name.read_bytes()).hexdigest()==current['sha256'])
      if ok:saved.append(current);print('CACHED_MUSEUM_EXTRA_DOCUMENT',url,flush=True);continue
    if was_fetched:time.sleep(10)
    was_fetched=True
    try:
      with urlopen(Request(url,headers={'User-Agent':'Mozilla/5.0 (MuseumBread official linked documents)','Accept':'application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document'}),timeout=40) as response:
        if response.status!=200:raise RuntimeError('Museum document not HTTP 200')
        raw=response.read(60_000_001)
    except HTTPError as ex:
      if ex.code not in (403,404):raise
      unavailable.append({**record,'http_status':ex.code})
      print('ORIGINAL_MUSEUM_DOC_ALREADY_UNAVAILABLE',ex.code,url,flush=True)
      continue
    if not 300<len(raw)<=60_000_000:raise RuntimeError('Original museum PDF/DOCX byte size invalid')
    ext=Path(path).suffix.lower()
    if not (ext=='.pdf' and raw.startswith(b'%PDF') or ext=='.docx' and raw.startswith(b'PK')):
      raise RuntimeError('Museum source file magic invalid '+url)
    sha=hashlib.sha256(raw).hexdigest();name=sha+ext
    (OUT/name).write_bytes(raw)
    saved.append({**record,'sha256':sha,'local_name':name,'size_bytes':len(raw)})
    print('DOWNLOADED_MUSEUM_EXTRA_DOCUMENT',i,len(originals),url,len(raw),flush=True)
  (OUT/'manifest.json').write_text(json.dumps({'source':HOST,'count':len(saved),'files':saved,'errors':[]},ensure_ascii=False,indent=2)+'\n')
  (OUT/'unavailable.json').write_text(json.dumps({'source':HOST,'count':len(unavailable),'files':unavailable},ensure_ascii=False,indent=2)+'\n')
  print('ORIGINAL_CROSSLINK_DOCUMENTS',len(saved),'real extra byte-preserved',len(unavailable),'already inaccessible',flush=True)
if __name__=='__main__':run()
