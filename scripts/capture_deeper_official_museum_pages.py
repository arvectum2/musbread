#!/usr/bin/env python3
"""Parse genuine museum source for newly discovered deep /node and exhibit URLs.
Originality is proven by archived HTTP bytes and their private sha; existing
indexed museum pages are not overwritten. Old 403/404 never get fake pages.
"""
from __future__ import annotations
import hashlib,json,re
from pathlib import Path
from urllib.parse import urlsplit
from lxml import html,etree
ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'apps/web/src/data'
PRIVATE=ROOT/'.local_archive/deep-original-museum-pages'
OUT=DATA/'official-deep-museum-pages.json'
HOST='https://muzei-xleb.ru'

def run():
 d=json.loads((PRIVATE/'manifest.json').read_text(encoding='utf-8'))
 if d.get('source')!=HOST or d.get('count')!=21 or len(d.get('pages',[]))!=21:
  raise RuntimeError('Deep original museum link HTTP scan is incomplete')
 native=set()
 for fname,key in [('official-museum-news.json','articles'),('official-museum-news-archive.json','articles'),
  ('official-exhibition-details.json','exhibitions'),('official-exhibition-archive.json','exhibitions'),
  ('official-exhibition-news-linked.json','exhibitions'),('official-node-linked-exhibitions.json','exhibitions'),
  ('official-original-legacy-sections.json','sections'),('official-museum-crosslink-pages.json','pages'),
  ('official-excursion-programs.json','programs'),('official-workshop-pages.json','programs'),
  ('official-exposition-rooms.json','rooms')]:
  original=json.loads((DATA/fname).read_text(encoding='utf-8'))
  native.update(urlsplit(r['source_url']).path.rstrip('/') for r in original[key] if r.get('source_url'))
 records={};redirects=[];unavailable=[];reused=[]
 for item in d['pages']:
  old=item['path'];status=item['status'];final=urlsplit(item['effective_url'])
  if final.netloc!='muzei-xleb.ru' or final.scheme!='https':
   raise RuntimeError('Original museum navigation left actual official site '+old)
  if status!=200:
   if status not in (403,404,410):raise RuntimeError('Unclassified museum page failure '+old+' '+str(status))
   unavailable.append({'path':old,'http_status':status,'effective_url':item['effective_url']});continue
  source=PRIVATE/(old.strip('/').replace('/','__')+'.html')
  raw=source.read_bytes()
  if hashlib.sha256(raw).hexdigest()!=item['source_html_sha256']:
   raise RuntimeError('Original museum HTTP HTML bytes altered '+old)
  doc=html.fromstring(raw);h1=doc.xpath('//h1')
  if len(h1)!=1:raise RuntimeError('Original museum page has ambiguous H1 '+old)
  title=' '.join(h1[0].text_content().split())
  if not title or title!=item['title']:
   raise RuntimeError('Museum H1 differs from original HTTP snapshot '+old)
  region=doc.xpath('//*[contains(concat(" ",normalize-space(@class)," ")," region-content ")]')
  if len(region)!=1:raise RuntimeError('Original museum page lost its real main region '+old)
  body=''.join(etree.tostring(ch,encoding='unicode',method='html') for ch in region[0] if ch.tag not in ('script','style'))
  if not 20<len(body)<2_000_000:raise RuntimeError('Untrustworthy museum body length '+old)
  current=final.path.rstrip('/')
  if not re.fullmatch(r'/(?:[a-z0-9-]+/)*[a-z0-9-]+',current):
   raise RuntimeError('Museum actual canonical path unsupported '+current)
  if old.startswith('/node/') and old!=current:
   redirects.append({'original_node':old,'effective_path':current,'http_status':200,
     'original_server_redirect_proven':True,'source_html_sha256':item['source_html_sha256']})
  if current in native:
   reused.append({'original_path':old,'existing_native_path':current});continue
  if current in records and records[current]['html_sha256']!=hashlib.sha256(body.encode()).hexdigest():
   raise RuntimeError('Different official museum documents conflict at canonical path '+current)
  # Images are taken ONLY from literal anchors in the archived museum
  # exhibition HTML, then matched to SHA-verified original museum binaries.
  # Do not infer a gallery from names or OCR scanned photos.
  image_links=[]
  if current.startswith('/vistavky/2019-06-21/'):
   from urllib.parse import urljoin
   for a in html.fragment_fromstring(body,create_parent='div').xpath('.//a[@href]'):
    linked=urlsplit(urljoin(HOST+current,a.get('href','')))
    if linked.netloc=='muzei-xleb.ru' and linked.path.startswith('/sites/default/files/vistavky/') and linked.path.lower().endswith(('.jpg','.jpeg','.png','.webp')):
     img_url=HOST+linked.path
     if img_url not in {img['url'] for img in image_links}:
      image_links.append({'url':img_url,'alt':title})
   if len(image_links)!=4:
    raise RuntimeError('Old museum exhibition four anchored images missing from immutable original body')
  records[current]={'source_url':HOST+current,'path':current,'title':title,'html':body,
   'html_sha256':hashlib.sha256(body.encode()).hexdigest(),
   'source_html_sha256':item['source_html_sha256'],
   'original_entry_path':old,'image_links':image_links,
   'source_page_captured_at':'2026-10-18'}
 result={'source':HOST,'count':len(records),'pages':list(records.values()),'redirects':redirects,
  'reused_existing':reused,'unavailable':unavailable}
 if len(records)+len(unavailable)<1:raise RuntimeError('No original museum pages verified')
 OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print('DEEP_MUSEUM_ACTUAL_SOURCE_PAGES',len(records),'distinct real HTML pages',len(redirects),'true old node redirects',len(unavailable),'museum 403/404',len(reused),'existing originals reused',flush=True)
 for x in result['pages']:print('AUTHENTIC_MUSEUM_SOURCE_PAGE',x['path'],x['title'][:55],len(x['html']),flush=True)
 for x in result['unavailable']:print('AUTHENTIC_MUSEUM_UNAVAILABLE',x,flush=True)
 return result
if __name__=='__main__':run()
