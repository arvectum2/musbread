#!/usr/bin/env python3
"""Download already-published source scientific records through configured Mac mini.

Two organizational source files only. Original bytes are private under SSD's
ignored .local_archive, never committed/published/converted into "academic"
papers. A separate published access policy is already cached by museum import.
"""
from __future__ import annotations
import json,hashlib,os,tempfile,zipfile
from datetime import datetime,timezone
from pathlib import Path
from urllib.request import Request,urlopen
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'apps/web/src/data/official-science-sources.json'
TARGET=ROOT/'.local_archive/science-originals'
CAP=50*1024*1024
def main():
    records=json.loads(SOURCE.read_text())
    if records.get('source')!='https://muzei-xleb.ru' or records.get('count')!=2:
        raise RuntimeError('Expected exactly two official science source pages')
    TARGET.mkdir(parents=True,exist_ok=True)
    entries=[]
    for item in records['pages']:
        if len(item['documents'])!=1:raise RuntimeError('Changed official document list')
        doc=item['documents'][0]
        url=doc['url'];ext=doc['format']
        if not url.startswith('https://muzei-xleb.ru/sites/default/files/page/') or ext not in ('pdf','docx'):
            raise RuntimeError('Untrusted document source')
        filename=hashlib.sha256(url.encode()).hexdigest()+'.'+ext
        dest=TARGET/filename
        if not dest.exists():
            req=Request(url,headers={'User-Agent':'Mozilla/5.0 (MuseumBread verified documentary cache)','Accept':'application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document'})
            with urlopen(req,timeout=90) as resp:
                if resp.status!=200:
                    raise RuntimeError('Museum source not HTTP 200 '+url)
                content_length=resp.headers.get('Content-Length')
                if content_length and int(content_length)>CAP:raise RuntimeError('Museum science doc >50MiB')
                data=resp.read(CAP+1)
            if len(data)>CAP or (content_length and len(data)!=int(content_length)):
                raise RuntimeError('Partial / oversized museum source bytes')
            if ext=='pdf' and not data.startswith(b'%PDF-'):
                raise RuntimeError('Expected real PDF magic')
            if ext=='docx' and not data.startswith(b'PK'):
                raise RuntimeError('Expected real DOCX archive')
            fd,temp=tempfile.mkstemp(prefix='science-',dir=TARGET)
            try:
                with os.fdopen(fd,'wb') as stream:stream.write(data)
                os.replace(temp,dest)
            finally:
                if os.path.exists(temp):os.unlink(temp)
        data=dest.read_bytes()
        if ext=='pdf' and not data.startswith(b'%PDF-'):raise RuntimeError('Cached science file is not PDF')
        if ext=='docx':
            with zipfile.ZipFile(dest) as archive:
                if 'word/document.xml' not in archive.namelist():raise RuntimeError('Malformed science DOCX')
                if archive.testzip():raise RuntimeError('Corrupted DOCX internal ZIP entry')
        entries.append({'source_url':url,'museum_title':doc['label'],'size_bytes':len(data),
            'sha256':hashlib.sha256(data).hexdigest(),'private_relative_file':filename})
        print('VERIFIED ORIGINAL',ext,len(data),'bytes',entries[-1]['sha256'],flush=True)
    manifest={'source':'https://muzei-xleb.ru','saved_utc':datetime.now(timezone.utc).isoformat(),
        'content_type':'scientific institutional documents, not academic publications',
        'files':entries}
    outfile=TARGET/'manifest.json'
    tmp=outfile.with_suffix('.json.tmp')
    tmp.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    tmp.replace(outfile)
    print('SAVED PRIVATE MANIFEST',outfile,'number_of_documents',len(entries))
if __name__=='__main__':main()
