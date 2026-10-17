#!/usr/bin/env python3
"""Local-only Russian OCR review material for public museum *scanned* PDFs.

No automatic accessibility approval, publication or modification of source PDFs.
OCR may contain mistakes. All extracted text stays in git-ignored ArvectumSSD.
"""
from __future__ import annotations
import argparse,concurrent.futures,hashlib,html,json,os,subprocess,tempfile
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
ARCHIVE=ROOT/'.local_archive/official-site-originals'
OUT=ROOT/'.local_archive/ocr-review'
SCANNED={
 '692d5743ed47e53b8bbf9522251b78770809193d26cc9feef4a1f622ce5d5f83',
 'c05fe1064dd45becbe976184900ab7318eb00ef0145988c915b76cfd092985c3',
 'ccaf820e83d229fa8d021d2381f648b5f8e90d6052acce6eb62c3892d8567064',
 'ef6be6b96f4aa1da0ccdb62fbb6da32fd03411a126487f64a9d8cb679fdc0332',
 '2e206de396dc3d404ec386dd4712efab46705d4afe9aad30bcd6625401d34c60',
}
def pages(path):
    result=subprocess.run(['pdfinfo',str(path)],capture_output=True,text=True,check=True)
    return int(next(x.split(':',1)[1].strip() for x in result.stdout.splitlines() if x.startswith('Pages:')))
def one_page(sha,pdf,page,dpi):
    folder=OUT/sha
    dest=folder/f'{page:03d}.txt'
    if dest.exists() and len(dest.read_text())>20:
        return page,len(dest.read_text()),'CACHED'
    with tempfile.TemporaryDirectory(prefix='ocrpage-',dir=OUT) as scratch:
        image=Path(scratch)/'page'
        render=['pdftoppm','-f',str(page),'-l',str(page),'-r',str(dpi),
                '-gray','-png','-singlefile',str(pdf),str(image)]
        subprocess.run(render,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,
                       check=True,timeout=80)
        env={**os.environ,'OMP_THREAD_LIMIT':'1'}
        ocr=subprocess.run(['tesseract',str(image)+'.png','stdout','-l','rus+eng',
                            '--psm','3'],env=env,capture_output=True,text=True,timeout=150)
        if ocr.returncode!=0:
            raise RuntimeError(f'page {page}: OCR {ocr.stderr[:240]}')
        cleaned='\n'.join(x.rstrip() for x in ocr.stdout.splitlines()).strip()
        dest.write_text(cleaned+'\n',encoding='utf-8')
        return page,len(cleaned),'OCR'
def make_review(sha,info,count):
    folder=OUT/sha
    records=[]
    for page in range(1,count+1):
        p=folder/f'{page:03d}.txt'
        if not p.is_file():raise RuntimeError('OCR page missing: '+str(p))
        text=p.read_text()
        records.append((page,text))
    heading=info['label']
    md=[
        '<!doctype html><html lang="ru"><head><meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        '<title>ЧЕРНОВИК OCR - '+html.escape(heading)+'</title></head><body>',
        '<h1>Текстовая версия для проверки редактором: '+html.escape(heading)+'</h1>',
        '<p><strong>НЕ УТВЕРЖДЕНО.</strong> Автоматическое распознавание может содержать ошибки в реквизитах, цифрах и правовых формулировках. Не использовать как действующий документ без постраничной сверки с официальным сканом.</p>',
        '<p>Оригинал: <a href="'+html.escape(info['url'],quote=True)+'">официальный документ музея</a>. Контрольная сумма: '+sha+'.</p>',
    ]
    for page,txt in records:
        md.append(f'<section aria-label="Страница {page}"><h2>Страница {page}</h2><pre style="white-space:pre-wrap;overflow-wrap:anywhere">{html.escape(txt)}</pre></section>')
    md.append('</body></html>')
    (folder/'draft-accessible-transcript.html').write_text('\n'.join(md),encoding='utf-8')
    manifest={
        'original_sha256':sha,'url':info['url'],'original_bytes':info['size_bytes'],
        'pages':count,'generated_utc':datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'status':'UNREVIEWED OCR / NOT LEGAL COPY / NOT ACCESSIBILITY APPROVED',
        'per_page_characters':{str(i):len(s) for i,s in records},
        'blank_or_short_pages':[i for i,s in records if len(s.strip())<30],
        'transcript_sha256':hashlib.sha256((folder/'draft-accessible-transcript.html').read_bytes()).hexdigest()
    }
    (folder/'review-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    return manifest

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--max-workers',type=int,default=3)
    parser.add_argument('--limit',type=int,default=5,help='Number of chosen documents to process')
    args=parser.parse_args()
    if not 1<=args.max_workers<=4:raise SystemExit('Max 4 OCR workers on Mac mini')
    archive=json.loads((ARCHIVE/'manifest.json').read_text())
    mapping={x['sha256']:x for x in archive['files']}
    docs=sorted(SCANNED,key=lambda sha:({ # shorter documents first
        'ccaf820e83d229fa8d021d2381f648b5f8e90d6052acce6eb62c3892d8567064':0,
        '2e206de396dc3d404ec386dd4712efab46705d4afe9aad30bcd6625401d34c60':1,
        'ef6be6b96f4aa1da0ccdb62fbb6da32fd03411a126487f64a9d8cb679fdc0332':2,
        '692d5743ed47e53b8bbf9522251b78770809193d26cc9feef4a1f622ce5d5f83':3,
        'c05fe1064dd45becbe976184900ab7318eb00ef0145988c915b76cfd092985c3':4
    })[sha])
    OUT.mkdir(parents=True,exist_ok=True)
    for sha in docs[:args.limit]:
        info=mapping[sha]
        pdf=ARCHIVE/info['local_name']
        assert pdf.stat().st_size==info['size_bytes']
        assert hashlib.sha256(pdf.read_bytes()).hexdigest()==sha
        count=pages(pdf)
        dpi=400 if count<=4 and sha.startswith('2e206') else 190
        (OUT/sha).mkdir(exist_ok=True)
        print('START',info['label'][:45],count,'pages','dpi',dpi,flush=True)
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.max_workers) as pool:
            futures=[pool.submit(one_page,sha,pdf,n,dpi) for n in range(1,count+1)]
            for j,fut in enumerate(concurrent.futures.as_completed(futures),1):
                page,length,status=fut.result()
                if j%8==0 or j==count:print('PROGRESS',j,'/',count,'page',page,'chars',length,status,flush=True)
        result=make_review(sha,info,count)
        print('DONE',info['label'][:40],'total chars',sum(result['per_page_characters'].values()),
              'short pages',result['blank_or_short_pages'][:12],flush=True)
if __name__=='__main__':main()
