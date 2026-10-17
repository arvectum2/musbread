#!/usr/bin/env python3
"""Only publish OCR *review metadata*, never unverified legal transcript text."""
from __future__ import annotations
import csv,hashlib,json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PRIVATE=ROOT/'.local_archive'
OUT=ROOT/'docs/tz-audit/OFFICIAL_PDF_OCR_REVIEW_20261018.csv'
STATUS='ЧЕРНОВИК OCR: не сверено редактором, не доступная утверждённая редакция'

def main():
    source=json.loads((PRIVATE/'official-site-originals/manifest.json').read_text())
    originals={x['sha256']:x for x in source['files']}
    rows=[]
    for file in sorted((PRIVATE/'ocr-review').glob('*/review-manifest.json')):
        item=json.loads(file.read_text())
        sh=item['original_sha256']
        origin=originals.get(sh)
        if origin is None or item['url']!=origin['url']:
            raise RuntimeError('Source OCR differs from official museum manifest')
        count=item['pages']
        if count<=0 or len(item['per_page_characters'])!=count:
            raise RuntimeError('OCR pages incomplete')
        transcript=file.parent/'draft-accessible-transcript.html'
        if hashlib.sha256(transcript.read_bytes()).hexdigest()!=item['transcript_sha256']:
            raise RuntimeError('OCR review HTML altered')
        pages=[file.parent/f'{i:03d}.txt' for i in range(1,count+1)]
        if any(not f.is_file() for f in pages):
            raise RuntimeError('OCR page missing')
        characters=sum(len(f.read_text().rstrip()) for f in pages)
        rows.append({
            'source_section':origin['source'],'original_title':origin['label'],
            'official_source_url':origin['url'],'original_sha256':sh,
            'scanned_pages':count,'ocr_characters_approx':characters,
            'short_or_blank_pages':len(item['blank_or_short_pages']),
            'private_review_path':'.local_archive/ocr-review/'+sh+'/draft-accessible-transcript.html',
            'review_status':STATUS,
        })
    if len(rows)!=5 or sum(x['scanned_pages'] for x in rows)!=125:
        raise RuntimeError('Expected precisely five source-backed scans, 125 pages')
    OUT.parent.mkdir(parents=True,exist_ok=True)
    with OUT.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]),delimiter=';',lineterminator='\n')
        w.writeheader();w.writerows(rows)
    print('REVIEW INVENTORY:',len(rows),'official scans, 125 pages,',
          sum(x['ocr_characters_approx'] for x in rows),'characters,',
          sum(x['short_or_blank_pages'] for x in rows),'empty/short OCR pages')
if __name__=='__main__':main()
