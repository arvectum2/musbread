#!/usr/bin/env python3
"""Non-modifying audit: all original PDFs open from isolated Nginx unchanged.

Tests only online download/opening mechanics: actual HTTP GET 200, application/pdf,
exact original SHA-256 bytes, proper PDF parser and unencrypted pages.
This test explicitly DOES NOT test PDF/UA, GOST, screen readers or OCR.
"""
from __future__ import annotations
import concurrent.futures as futures
import csv, hashlib, http.client, json, os, re, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from export_official_museum_original_documents import source_documents
HOST='127.0.0.1';PORT=int(os.environ.get('MUSBREAD_NGINX_PORT','18088'))
REPORT=ROOT/'docs/tz-audit/ORIGINAL_MUSEUM_PDF_OPENABILITY_HTTP_20261019.csv'
SUMMARY=ROOT/'docs/tz-audit/ORIGINAL_MUSEUM_PDF_OPENABILITY_HTTP_20261019.json'

def audit_one(entry):
 path, info = entry
 if info['format']!='pdf':raise ValueError('Only PDF')
 c=http.client.HTTPConnection(HOST, PORT, timeout=40)
 sha=hashlib.sha256();length=0;magic=b''
 try:
  c.request('GET',path,headers={'Host':'muzei-xleb.ru','User-Agent':'MusBread-PDF-viewability-local-QA/1.0'})
  response=c.getresponse(); status=response.status
  headers=dict((key.lower(),value) for key,value in response.getheaders())
  while True:
   block=response.read(1024*1024)
   if not block:break
   if not magic:magic=block[:5]
   sha.update(block);length+=len(block)
 finally:c.close()
 source_path=info['source_file']; local=ROOT/'apps/web/out'/path.lstrip('/')
 pdf=subprocess.run(['pdfinfo',str(local)],capture_output=True,text=True,timeout=35)
 pages=int(re.search(r'^Pages:\s+(\d+)',pdf.stdout,re.M).group(1)) if re.search(r'^Pages:\s+(\d+)',pdf.stdout,re.M) else 0
 encryption=re.search(r'^Encrypted:\s+(.*)$',pdf.stdout,re.M)
 issues=[]
 if status!=200:issues.append('HTTP_NOT_200')
 if headers.get('x-musbread-local-test')!='isolated':issues.append('NOT_ISOLATED_NGINX')
 if not headers.get('content-type','').lower().startswith('application/pdf'):issues.append('NOT_APPLICATION_PDF_MIME')
 if 'attachment' in headers.get('content-disposition','').lower():issues.append('FORCED_DOWNLOAD_NOT_VIEW')
 if magic!=b'%PDF-':issues.append('NOT_PDF_MAGIC')
 if length!=info['size_bytes'] or int(headers.get('content-length','-1'))!=info['size_bytes']:issues.append('BYTE_LENGTH_CHANGED')
 if sha.hexdigest()!=info['sha256']:issues.append('SOURCE_SHA256_CHANGED')
 if not local.is_file() or local.stat().st_size!=info['size_bytes']:issues.append('LOCAL_SOURCE_MISSING')
 if pdf.returncode or pages<1:issues.append('PDF_PARSER_CANNOT_OPEN')
 if encryption and not encryption.group(1).strip().lower().startswith('no'):issues.append('PDF_ENCRYPTED')
 # Test actually decoding and rendering the first page from every PDF as an
 # in-memory PNG via Poppler. No file is modified, no OCR or text extraction.
 try:
  render=subprocess.run(['pdftoppm','-f','1','-l','1','-singlefile','-scale-to','160','-png',str(local)],capture_output=True,timeout=50)
  rendered=render.returncode==0 and render.stdout.startswith(b'\x89PNG\r\n\x1a\n')
 except subprocess.TimeoutExpired:
  rendered=False
 if not rendered:issues.append('PDF_FIRST_PAGE_RENDER_FAILED')
 return {'Путь на сайте':path,'Результат':'PASS' if not issues else 'FAIL','HTTP':status,
         'MIME':headers.get('content-type',''),'Байт':length,'Страниц':pages,
         'SHA256 совпадает':'да' if sha.hexdigest()==info['sha256'] else 'нет',
         'Inline (не форсируется скачивание)':'да' if 'attachment' not in headers.get('content-disposition','').lower() else 'нет',
         'Отрисовка первой страницы':'да' if rendered else 'нет',
         'Ошибка':'; '.join(issues)}

def run():
 if HOST!='127.0.0.1' or not 1024<=PORT<=65535:raise RuntimeError('Only isolated loopback Nginx test is authorized')
 docs=source_documents(); pdfs=sorted([(p,i) for p,i in docs.items() if i['format']=='pdf'])
 assert len(docs)==101 and len(pdfs)==96
 with futures.ThreadPoolExecutor(max_workers=4) as pool:
  results=list(pool.map(audit_one,pdfs))
 with REPORT.open('w',encoding='utf-8-sig',newline='') as f:
  writer=csv.DictWriter(f,fieldnames=list(results[0]),delimiter=';',lineterminator='\n');writer.writeheader();writer.writerows(results)
 summary={'checked_pdf':len(results),'passed':sum(r['Результат']=='PASS' for r in results),
          'failed':sum(r['Результат']=='FAIL' for r in results),
          'total_bytes':sum(r['Байт'] for r in results),
          'total_pages':sum(r['Страниц'] for r in results),
          'first_pages_rendered':sum(r['Отрисовка первой страницы']=='да' for r in results),
          'verified':'All original PDFs served intact via HTTP 200, inline application/pdf and rendered by Poppler PDF engine',
          'not_verified':'This is NOT a screen-reader, tagged PDF or GOST/PDF-UA accessibility test',
          'no_pdf_modified':True,'no_ocr_performed':True,'network':'127.0.0.1 isolated Nginx only',
          'report':'docs/tz-audit/'+REPORT.name}
 SUMMARY.write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print('MUSEUM_96_ORIGINAL_PDF_GET_RENDERABLE_AUDIT '+json.dumps(summary,ensure_ascii=False),flush=True)
 if summary['failed']:
  print('FIRST_FAILURES',[(r['Путь на сайте'],r['Ошибка']) for r in results if r['Результат']=='FAIL'][:12])
  raise SystemExit(1)
 return summary
if __name__=='__main__':run()
