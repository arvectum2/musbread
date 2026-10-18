#!/usr/bin/env python3
"""Save official PDF bytes unchanged on SSD. Do not OCR/reprocess scans."""
from __future__ import annotations
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.parse import urlparse
from hashlib import sha256
import json,time
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'apps/web/src/data/official-museum-menu-gaps.json'
DIR=ROOT/'.local_archive/official-menu-originals'
MANIFEST=DIR/'manifest.json'
MAX_BYTES=40*1024*1024
def main():
 d=json.loads(SOURCE.read_text())
 assert d['source']=='https://muzei-xleb.ru'
 pagepaths={'/uchetnaya-politika','/protivodeystvie-terrorizmu','/antimonopolnyy-komplaens'}
 items=[]
 for p in d['pages']:
  if p['path'] not in pagepaths:continue
  for link in p['document_links']:
   url=link['url']
   assert urlparse(url).hostname=='muzei-xleb.ru'
   assert urlparse(url).path.startswith('/sites/default/files/')
   assert urlparse(url).path.lower().endswith('.pdf')
   items.append({'source':p['path'],'url':url,'label':link['label']})
 assert len(items)==11,(len(items),'source menu changed')
 DIR.mkdir(parents=True,exist_ok=True)
 cached=[];fail=[]
 for i,item in enumerate(items):
  if i:time.sleep(10)
  req=Request(item['url'],headers={'User-Agent':'Mozilla/5.0 (MusBread official original PDF preservation)'})
  try:
   with urlopen(req,timeout=50) as response:
    if response.status!=200 or 'pdf' not in response.headers.get('Content-Type','').lower():
     raise ValueError('Not official PDF 200')
    buf=response.read(MAX_BYTES+1)
    if len(buf)>MAX_BYTES or not buf.startswith(b'%PDF-') or b'%%EOF' not in buf[-2048:]:
     raise ValueError('Original PDF invalid/too big')
    contentlength=response.headers.get('Content-Length')
    if contentlength and int(contentlength)!=len(buf):
     raise ValueError('Original PDF truncated')
   digest=sha256(buf).hexdigest()
   dst=DIR/(digest+'.pdf')
   if dst.exists():
    if dst.read_bytes()!=buf:raise ValueError('Cached original same digest mismatch')
   else: dst.write_bytes(buf)
   cached.append({**item,'local_name':dst.name,'size_bytes':len(buf),'sha256':digest})
   print('OK',i+1,'/',len(items),len(buf),item['label'][:65],flush=True)
  except Exception as e:
   fail.append({'url':item['url'],'error':type(e).__name__})
   print('SKIP',i+1,'/',len(items),type(e).__name__,flush=True)
 manifest={'source':'https://muzei-xleb.ru','source_capture':SOURCE.name,'count':len(cached),'files':cached,'errors':fail}
 tmp=DIR/'manifest.json.tmp'
 tmp.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
 tmp.replace(MANIFEST)
 print('DONE',len(cached),'/',len(items),'authentic PDF cached on external SSD',flush=True)
if __name__=='__main__':main()
