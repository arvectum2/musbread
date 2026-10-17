#!/usr/bin/env python3
"""Cache unchanged official museum PDFs/DOCXs outside public Git for later CMS upload.

Never rewrite the legal text; preserve exact URL, SHA256, and download date.
Manual, rate-limited; do not use this as an unattended sync on museum servers.
"""
from __future__ import annotations
import argparse,json,mimetypes,time
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request,urlopen
from hashlib import sha256
from datetime import datetime,timezone

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'apps/web/src/data/official-page-snapshots.json'
ARCHIVE=ROOT/'.local_archive/official-site-originals'

def main():
 ap=argparse.ArgumentParser()
 ap.add_argument('--max-files',type=int,default=12)
 ap.add_argument('--delay',type=float,default=10)
 args=ap.parse_args()
 if args.delay<10:raise SystemExit('Respect official site robots Crawl-delay: 10')
 data=json.loads(SOURCE.read_text())
 ordered=['/politika-konfidencialnosti-i-obrabotki-personalnyh-dannyh',
  '/ceny-i-usloviya-predostavleniya-uslug','/oficialnye-dokumenty-muzeya',
  '/stoimost','/politika-obespecheniya-usloviy-dostupnosti-dlya-invalidov-i-drugih-mobilnyh-grazhdan']
 page_map={x['path']:x for x in data['pages']}
 links={}
 for src in ordered:
  for doc in page_map[src]['document_links']:
   links.setdefault(doc['url'],{'url':doc['url'],'label':doc['label'],'source':src})
 ARCHIVE.mkdir(parents=True,exist_ok=True)
 results=[]; errors=[]
 for i,record in enumerate(list(links.values())[:args.max_files]):
  if i:time.sleep(args.delay)
  link=record['url']; suffix=Path(urlparse(link).path).suffix.lower()
  if suffix not in ('.pdf','.docx','.doc','.xlsx','.xls'):continue
  try:
   with urlopen(Request(link,headers={'User-Agent':'Mozilla/5.0 (MusBread official document source verifier)'}),timeout=18) as response:
    if response.status!=200: raise ValueError(f'HTTP {response.status}')
    declared=response.headers.get('Content-Length')
    raw=response.read(100_000_001)
    if len(raw)>100_000_000:raise ValueError('File larger than safe 100 MB cap')
    if declared is not None and len(raw)!=int(declared):
     raise ValueError('Truncated document: received %s vs %s bytes'%(len(raw),declared))
    typ=response.headers.get('Content-Type','')
   expected_pdf=suffix=='.pdf'
   if expected_pdf and not raw.startswith(b'%PDF-'):raise ValueError('Not a PDF')
   if suffix in ('.docx','.xlsx') and not raw.startswith(b'PK\x03\x04'):raise ValueError('Not Office OpenXML')
   digest=sha256(raw).hexdigest()
   dest=ARCHIVE/(digest+suffix)
   if not dest.exists(): dest.write_bytes(raw)
   record.update({'local_name':dest.name,'sha256':digest,'size_bytes':len(raw),
    'content_type':typ,'retrieved_utc':datetime.now(timezone.utc).isoformat(timespec='seconds')})
   results.append(record)
   print('OK',len(results),record['label'][:50],dest.name[:18],len(raw),flush=True)
  except Exception as exc:
   errors.append({'url':link,'error':type(exc).__name__})
   print('FAIL',type(exc).__name__,link,flush=True)
 (ARCHIVE/'manifest.json').write_text(json.dumps({
  'source':'https://muzei-xleb.ru','generated_utc':datetime.now(timezone.utc).isoformat(timespec='seconds'),
  'files':results,'errors':errors
 },ensure_ascii=False,indent=2)+'\n')
 print('ARCHIVE',len(results),'files',len(errors),'errors',ARCHIVE,flush=True)

if __name__=='__main__':main()
