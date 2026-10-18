#!/usr/bin/env python3
"""Direct Mac mini original-source verification of extra museum links after full page import."""
from __future__ import annotations
import csv,json,time,hashlib
from urllib.request import Request,urlopen
from urllib.error import HTTPError
from lxml import html
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CSV=ROOT/'docs/seo/ORIGINAL_MUSEUM_CROSSLINK_GAPS_20261018.csv'
OUT=ROOT/'.local_archive/museum-crosslink-original-pages'
HOST='https://muzei-xleb.ru'
def main():
 with CSV.open(encoding='utf-8-sig',newline='') as f:r=list(csv.DictReader(f,delimiter=';'))
 paths=sorted({x['linked_path'] for x in r if x['gap_type']=='UNCOVERED_ORIGINAL_MUSEUM_PAGE'})
 if len(paths)!=18:raise RuntimeError('Original crosslink list changed: '+str(len(paths)))
 OUT.mkdir(parents=True,exist_ok=True)
 saved=json.loads((OUT/'manifest.json').read_text(encoding='utf-8')) if (OUT/'manifest.json').exists() else {'source':HOST,'pages':[]}
 done={x['path']:x for x in saved['pages']}
 just_fetched=False
 for path in paths:
  if path in done:
   print('SOURCE_PREVIOUSLY_VERIFIED',path,done[path]['status'],flush=True);continue
  if just_fetched:time.sleep(10)
  just_fetched=True
  try:
   with urlopen(Request(HOST+path,headers={'User-Agent':'Mozilla/5.0 (MuseumBread source crosslink provenance)','Accept':'text/html'}),timeout=32) as result:
    raw=result.read(2_000_000);status=result.status;url=result.geturl();ctype=result.headers.get('Content-Type','')
   if 'text/html' not in ctype:raise RuntimeError('Unexpected type '+path)
   tree=html.fromstring(raw)
   headers=tree.xpath('//h1')
   title=' '.join(headers[0].text_content().split()) if headers else ''
   record={'path':path,'status':status,'effective_url':url,'source_html_sha256':hashlib.sha256(raw).hexdigest(),'h1':title,'html_len':len(raw),'content_type':ctype}
   (OUT/(path.strip('/').replace('/','__')+'.html')).write_bytes(raw)
  except HTTPError as exc:
   record={'path':path,'status':exc.code,'effective_url':exc.geturl(),'h1':'','source_html_sha256':''}
  done[path]=record
  (OUT/'manifest.json').write_text(json.dumps({'source':HOST,'count':len(done),'pages':list(done.values())},ensure_ascii=False,indent=2)+'\n')
  print('MUSEUM_ORIGINAL_EXTRA_LINK',record,flush=True)
 print('DONE',len(done),'of',len(paths),flush=True)
if __name__=='__main__':main()
