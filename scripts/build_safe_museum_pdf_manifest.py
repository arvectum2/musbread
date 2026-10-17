#!/usr/bin/env python3
"""Build offline SHA256-verified local manifest for 3 reconstructed museum PDFs.

Does not approve accessibility; does not publish or relax Laravel PDF controls.
"""
import hashlib,json,subprocess
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PRIVATE=ROOT/'.local_archive'
ORIGINALS=PRIVATE/'official-site-originals'
PDFS=PRIVATE/'pdf-compression'
SPEC=[
 ('ccaf820e83d229fa8d021d2381f648b5f8e90d6052acce6eb62c3892d8567064',
  'safe_museum_equipment_q70.pdf','museum-finance',2),
 ('ef6be6b96f4aa1da0ccdb62fbb6da32fd03411a126487f64a9d8cb679fdc0332',
  'safe_museum_annual_2023_q70.pdf','museum-finance',32),
 ('2e206de396dc3d404ec386dd4712efab46705d4afe9aad30bcd6625401d34c60',
  'safe_museum_anticorruption_2018_q70.pdf','museum-anti-corruption',4),
]

def pages(file):
    res=subprocess.run(['pdfinfo',str(file)],capture_output=True,text=True,check=True)
    return int(next(x.split(':')[1] for x in res.stdout.splitlines() if x.startswith('Pages:')))

def main():
    source=json.loads((ORIGINALS/'manifest.json').read_text())
    assert source['source']=='https://muzei-xleb.ru'
    origin={x['sha256']:x for x in source['files']}
    copies=[]
    for sh,local,owner,count in SPEC:
        info=origin[sh]
        original=ORIGINALS/info['local_name']
        transformed=PDFS/local
        assert original.stat().st_size==info['size_bytes']
        assert hashlib.sha256(original.read_bytes()).hexdigest()==sh
        data=transformed.read_bytes()
        assert data.startswith(b'%PDF-') and b'%%EOF' in data[-2048:]
        assert 16<=len(data)<=15*1024*1024
        assert pages(original)==pages(transformed)==count
        assert '/finansovo-hozyaystvennaya-deyatelnost'==info['source'] if owner=='museum-finance' else info['source']=='/protivodeystvie-korrupcii'
        copies.append({
            'source_url':info['url'],
            'source_sha256':sh,'source_size_bytes':info['size_bytes'],
            'source_page':info['source'],'target_cms_slug':owner,
            'source_label':info['label'],
            'derived_file':local,'derived_sha256':hashlib.sha256(data).hexdigest(),
            'derived_size_bytes':len(data),'pages':count,
            'accessibility_reviewed':False,
        })
        print('VERIFIED',owner,count,'pages',info['label'][:45],len(data),'bytes')
    payload={'source':'https://muzei-xleb.ru',
             'captured_utc':datetime.now(timezone.utc).isoformat(timespec='seconds'),
             'type':'UNREVIEWED_RASTERIZED_PDF_DERIVATIVES',
             'copies':copies}
    output=PDFS/'verified-derivatives.json'
    output.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n')
    print('PRIVATE MANIFEST',output,'items',len(copies))
if __name__=='__main__':main()
