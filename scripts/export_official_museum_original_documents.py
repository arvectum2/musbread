#!/usr/bin/env python3
"""Export original bytes of public museum PDF/DOCX to original Drupal paths.

All 57 source documents are already privately archived on user's Mac mini SSD.
No OCR, recompression, rewriting or Git binary commit. Destination is Next's
OUT/ at the same URL path used by the existing museum. This is opt-in because
a Git-only deployment does not contain ArvectumSSD private originals.
"""
from __future__ import annotations
import argparse,hashlib,json,os,re,shutil
from pathlib import Path
from urllib.parse import urlsplit
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'apps/web/out'
MANIFESTS=[ROOT/p for p in (
 '.local_archive/official-site-originals',
 '.local_archive/official-menu-originals',
 '.local_archive/science-originals',
 '.local_archive/news-original-documents',
 '.local_archive/extra-original-documents',
 '.local_archive/deep-original-documents',
)]
DEPLOYMENT_LIST=ROOT/'docs/source-migration/OFFICIAL_ORIGINAL_DOCUMENTS_DEPLOYMENT_20261018.json'
FILE_URL=re.compile(r'^/sites/default/files/[A-Za-z0-9._~!$&\x27()*+,;=:@%/-]+\.(?:pdf|docx)$',re.I)

def signature(path:Path):
    h=hashlib.sha256()
    with path.open('rb') as src:
        for block in iter(lambda:src.read(1048576),b''):h.update(block)
    return h.hexdigest()

def source_documents():
    records={}
    for folder in MANIFESTS:
        source_manifest=folder/'manifest.json'
        if folder.name in ('news-original-documents','extra-original-documents','deep-original-documents') and not source_manifest.exists():
            continue  # Fully source-verified news documents not discovered yet
        data=json.loads(source_manifest.read_text())
        if data.get('source')!='https://muzei-xleb.ru' or data.get('errors',[])!=[]:
            raise RuntimeError('Museum source manifest not approved/verified '+str(folder))
        for item in data['files']:
            uri=item.get('url') or item.get('source_url')
            u=urlsplit(uri)
            path=u.path
            if u.scheme!='https' or u.netloc!='muzei-xleb.ru' or u.query or not FILE_URL.fullmatch(path):
                raise RuntimeError('Unsafe original museum document URL '+str(uri))
            sha=item.get('sha256','')
            size=item.get('size_bytes')
            name=item.get('local_name') or item.get('private_relative_file')
            if not re.fullmatch(r'[a-f0-9]{64}',sha) or not isinstance(size,int) or size<1:
                raise RuntimeError('Unverified source document sha or size '+path)
            if not name or Path(name).name!=name or not re.fullmatch(r'[a-f0-9]{64}\.(pdf|docx)',name):
                raise RuntimeError('Unsafe private archive basename '+str(name))
            source=folder/name
            if path in records:
                r=records[path]
                if r['sha256']!=sha or r['size_bytes']!=size:raise RuntimeError('Museum document duplicate URL differs: '+path)
                continue
            records[path]={'url':uri,'legacy_path':path,'sha256':sha,'size_bytes':size,
                           'format':Path(path).suffix[1:],'source_file':source}
    if len(records)<57:raise RuntimeError('Baseline 57 museum original documents missing')
    new_manifest=ROOT/'.local_archive/news-original-documents/manifest.json'
    if new_manifest.exists():
        news_count=json.loads(new_manifest.read_text()).get('count')
        if len(records)<57+news_count:raise RuntimeError('Linked museum historical PDFs not present in cutover static archive')
    return records

def export(*,apply=False,verify_only=False):
    if apply and verify_only:raise ValueError('Cannot copy and verify at once')
    docs=source_documents()
    if not OUT.is_dir():raise RuntimeError('Run Next.js static build first')
    bytes_count=0;copied=0;already=0
    for path,r in sorted(docs.items()):
        private=r['source_file']
        if not private.is_file() or private.stat().st_size!=r['size_bytes'] or signature(private)!=r['sha256']:
            raise RuntimeError('Altered or missing original museum document: '+path)
        with private.open('rb') as fd:magic=fd.read(4)
        if not (r['format']=='pdf' and magic.startswith(b'%PDF') or r['format']=='docx' and magic.startswith(b'PK')):
            raise RuntimeError('Source museum document type does not match verified PDF/DOCX bytes: '+path)
        output=OUT/path.lstrip('/')
        if output.is_symlink():raise RuntimeError('Refusing symlink document target '+str(output))
        if output.exists():
            if not output.is_file() or output.stat().st_size!=r['size_bytes'] or signature(output)!=r['sha256']:
                raise RuntimeError('Existing wrong document bytes at new museum path '+path)
            already+=1
        elif verify_only:
            raise RuntimeError('Original museum document missing from deployable static site '+path)
        elif apply:
            output.parent.mkdir(parents=True,exist_ok=True)
            temp=output.with_suffix(output.suffix+'.tmp')
            try:
                with private.open('rb') as src,temp.open('wb') as dst:
                    shutil.copyfileobj(src,dst,length=1048576)
                if temp.stat().st_size!=r['size_bytes'] or signature(temp)!=r['sha256']:
                    raise RuntimeError('Museum source bytes altered during deployment copy '+path)
                os.replace(temp,output)
            finally:
                if temp.exists():temp.unlink()
            copied+=1
        bytes_count+=r['size_bytes']
    summary={'source':'https://muzei-xleb.ru',
             'description':'Copied byte-for-byte from user-owned original source files on Mac mini; not included in git.',
             'count':len(docs),'total_bytes':bytes_count,
             'files':[{'legacy_path':p,**{k:v for k,v in r.items() if k!='source_file'}} for p,r in sorted(docs.items())]}
    if apply:
        DEPLOYMENT_LIST.write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    elif verify_only:
        saved=json.loads(DEPLOYMENT_LIST.read_text(encoding='utf-8'))
        if saved!=summary:raise RuntimeError('Museum source documents deploy list not up to date')
    print('MUSEUM_ORIGINAL_DOCS',len(docs),'PDF/DOCX','total',f'{bytes_count/1048576:.2f} MiB',
          'copied',copied,'already',already,'verified' if verify_only else 'applied' if apply else 'dry-run',flush=True)
    return summary
if __name__=='__main__':
    ap=argparse.ArgumentParser()
    mode=ap.add_mutually_exclusive_group()
    mode.add_argument('--apply',action='store_true')
    mode.add_argument('--verify-only',action='store_true')
    args=ap.parse_args()
    export(apply=args.apply,verify_only=args.verify_only)
