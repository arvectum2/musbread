#!/usr/bin/env python3
"""Fetch actual museum primary listing pages only through Mac mini source network.
Do not infer or invent original body content. Respect source crawl delay.
"""
from __future__ import annotations
import hashlib,json,time
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.error import HTTPError
from lxml import html
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'.local_archive/remaining-museum-original-section-html'
SOURCE='https://muzei-xleb.ru'
PAGES=['/informaciya-dlya-dariteley','/master-klassy','/novosty','/posetitelyam','/video','/vistavky']
def main():
 OUT.mkdir(parents=True,exist_ok=True)
 results=[]
 for i,path in enumerate(PAGES):
  if i:time.sleep(10)
  try:
   with urlopen(Request(SOURCE+path,headers={'User-Agent':'Mozilla/5.0 (MuseumBread authentic source preservation)','Accept':'text/html'}),timeout=30) as response:
    raw=response.read(3_000_000);status=response.status;url=response.geturl();ctype=response.headers.get('Content-Type','')
   if status!=200 or 'text/html' not in ctype:raise ValueError('Unexpected original type/status '+str(status)+' '+ctype)
   tree=html.fromstring(raw)
   titles=[' '.join(x.text_content().split()) for x in tree.xpath('//h1')]
   body=[(' '.join(x.text_content().split())[:140],len(' '.join(x.text_content().split())),len(x.xpath('.//a[@href]'))) for x in tree.xpath('//*[contains(concat(" ",normalize-space(@class)," ")," field-name-body ")]')]
   views=[(' '.join(x.text_content().split())[:140],len(' '.join(x.text_content().split())),len(x.xpath('.//a[@href]'))) for x in tree.xpath('//*[contains(concat(" ",normalize-space(@class)," ")," view-content ")]')]
   (OUT/(path[1:]+'.html')).write_bytes(raw)
   result={'path':path,'status':status,'effective':url,'sha256':hashlib.sha256(raw).hexdigest(),'titles':titles,'bodies':body[:3],'views':views[:3]}
  except HTTPError as err:result={'path':path,'status':err.code,'effective':err.geturl()}
  results.append(result)
  print('TRUE_MUSEUM_OLD_SECTION',result,flush=True)
 (OUT/'verification.json').write_text(json.dumps({'source':SOURCE,'count':len(results),'pages':results},ensure_ascii=False,indent=2)+'\n')
if __name__=='__main__':main()
