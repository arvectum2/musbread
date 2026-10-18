#!/usr/bin/env python3
"""Read-only official-site PDF/office accessibility inventory.

Mac mini private originals MUST remain git-ignored on ArvectumSSD.
This is technical preflight, NOT PDF/UA or GOST R 70176-2022 certification.
No OCR and no copying source document contents.
"""
from __future__ import annotations

import csv
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
PRIVATE=ROOT/'.local_archive/official-site-originals'
MANIFEST=PRIVATE/'manifest.json'
REPORT=ROOT/'docs/tz-audit/OFFICIAL_PDF_ACCESSIBILITY_PREFLIGHT.csv'
REPORT_MD=ROOT/'docs/TZ211_212_213_OFFICIAL_DOCUMENT_ACCESSIBILITY_20261018.md'


def run(args:list[str],timeout:int=25)->subprocess.CompletedProcess:
    return subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                          timeout=timeout,check=False)

def inspect(item:dict)->dict:
    path=PRIVATE/item['local_name']
    if not path.is_file():
        raise RuntimeError('Source missing '+item['local_name'])
    original=sha256(path.read_bytes()).hexdigest()
    if original!=item['sha256'] or path.stat().st_size!=item['size_bytes']:
        raise RuntimeError('Original source SHA/size mismatch '+item['local_name'])
    data={
      'source_section':item.get('source',''),
      'label':item.get('label',''),
      'url':item['url'],
      'sha256':original,
      'format':path.suffix.lstrip('.').lower(),
      'size_bytes':item['size_bytes'],
      'page_count':'',
      'pdf_tagged':'',
      'first_3_pages_text_chars':'',
      'first_3_pages_meaningful_text':'',
      'risk':'',
    }
    if data['format']!='pdf':
        data['risk']='DOCX: structural accessibility needs separate manual and AT check'
        return data
    info=run(['pdfinfo',str(path)])
    if info.returncode!=0:
        raise RuntimeError('pdfinfo cannot parse '+path.name)
    metadata={}
    for line in info.stdout.decode('utf-8','replace').splitlines():
        if ':' in line:
            k,v=line.split(':',1)
            metadata[k.strip()]=v.strip()
    pages=int(metadata.get('Pages','0'))
    if not (1<=pages<=500):
        raise RuntimeError('PDF page count invalid for '+path.name)
    tagged=metadata.get('Tagged','unknown').lower()
    if tagged not in ('yes','no','unknown'):
        tagged='unknown'
    # Small bounded technical sample; no OCR, not proof of semantic meaning.
    sample=run(['pdftotext','-f','1','-l',str(min(pages,3)),
                '-enc','UTF-8',str(path),'-'],timeout=35)
    txt=sample.stdout.decode('utf-8','replace') if sample.returncode==0 else ''
    chars=len(''.join(c for c in txt if c.isalnum()))
    data.update(page_count=pages,pdf_tagged=tagged,
        first_3_pages_text_chars=chars,
        first_3_pages_meaningful_text=('likely' if chars>=150 else
                                      'insufficient' if chars<150 else 'unknown'))
    if tagged!='yes' and chars<150:
        data['risk']='HIGH: untagged and little extractable text (likely scanned)'
    elif tagged!='yes':
        data['risk']='HIGH: untagged PDF despite extractable text'
    elif chars<150:
        data['risk']='HIGH: tagged PDF with little extractable text in sampled pages'
    else:
        data['risk']='REVIEW: tagged with extractable text; semantics, order, tables, PDF/UA still unverified'
    return data


def inventory(manifest:dict)->list[dict]:
    if manifest.get('source')!='https://muzei-xleb.ru':
        raise RuntimeError('Unexpected source')
    entries=manifest.get('files')
    if not isinstance(entries,list) or len(entries)!=44:
        raise RuntimeError('Expected 44 actual original museum sources')
    rows=[inspect(item) for item in entries]
    if len({item['sha256'] for item in rows})!=len(rows):
        raise RuntimeError('Source hashes repeated')
    if not any(row['format']=='pdf' for row in rows):
        raise RuntimeError('No original PDFs')
    return rows


def publish(rows:list[dict])->None:
    REPORT.parent.mkdir(parents=True,exist_ok=True)
    with REPORT.open('w',encoding='utf-8-sig',newline='') as f:
        # LF endings keep the audit readable on Mac/Linux/CI and prevent
        # Git treating the standard CRLF CSV writer suffix as whitespace.
        w=csv.DictWriter(f,fieldnames=list(rows[0]),delimiter=';',
                         lineterminator='\n')
        w.writeheader();w.writerows(rows)
    c=Counter(r['format'] for r in rows)
    t=Counter(r['pdf_tagged'] for r in rows if r['format']=='pdf')
    low=[r for r in rows if r['format']=='pdf'
         and r['first_3_pages_meaningful_text']=='insufficient']
    untagged=[r for r in rows if r['format']=='pdf' and r['pdf_tagged']!='yes']
    ntext=sum(1 for r in rows if r['format']=='pdf' and r['first_3_pages_meaningful_text']=='likely')
    lines=[
      '# TZ-211/212/213 — доступность настоящих официальных документов музея',
      '',
      'Проверка 18.10.2026. Источники: действующий сайт https://muzei-xleb.ru'
      ' через Mac mini, SHA-256 и длина каждого файла сравнены с ранее'
      ' сохранённым закрытым оригиналом на внешнем ArvectumSSD.',
      '',
      '**Это технический preflight, а не сертификация PDF/UA, ГОСТ Р'
      ' 70176-2022 или постановления № 102.** Наличие текстового слоя'
      ' не доказывает доступность семантической структуры, языка, таблиц,'
      ' порядка чтения и графических альтернатив. Тегированный PDF'
      ' тоже требует ручной проверки вспомогательными технологиями.',
      '',
      f'- Проверено исходных документов: **{len(rows)}**.',
      f'- Форматы: PDF **{c["pdf"]}**, DOCX **{c["docx"]}**.',
      f'- PDF с Tagged: yes — **{t["yes"]}**, без тегов — **{t["no"]}**'
      f', неизвестно — **{t["unknown"]}**.',
      f'- Есть извлекаемые 150+ букв/цифр на первых трёх страницах'
      f' (приближённая оценка, не ГОСТ): **{ntext}** PDF.',
      f'- Недостаточно извлекаемого текста в первых трёх страницах'
      f' (возможны сканы, титульные листы или краткий PDF): **{len(low)}**.',
      '',
      '## Первые действия по устранению',
      '',
      'Для PDF без структурных тегов нельзя выдавать обычный текстовый слой'
      ' за доступный PDF. Требуется согласованный с заказчиком способ:'
      ' исправление тегов/закладок/порядка чтения и проверка'
      ' экранным диктором либо точная эквивалентная HTML-версия.',
      'Для документов с подозрением на сканы нужна визуальная проверка'
      ' страниц, правомерный OCR при необходимости и обязательная'
      ' вычитка фактического официального текста, без генерации'
      ' вымышленных юридических формулировок.',
      'DOCX тоже требуют отдельной проверки заголовков, таблиц, alt'
      ' и корректной последовательности чтения.',
      '',
      'Полная таблица с официальной страницей, URL, названием,'
      ' SHA-256, размером, числом страниц, признаками PDF Tagged и'
      ' ограниченными текстовыми пробами:'
      ' [OFFICIAL_PDF_ACCESSIBILITY_PREFLIGHT.csv]'
      '(tz-audit/OFFICIAL_PDF_ACCESSIBILITY_PREFLIGHT.csv).',
      '',
      '### Приоритетные проблемные документы',
      '',
    ]
    for r in low[:15]:
        lines.append('- **'+r['label'].replace('\n',' ').replace('|',' ')[:150]+'**'
                     +' — '+str(r['page_count'])+' стр., tagged='+r['pdf_tagged']
                     +', образец: '+str(r['first_3_pages_text_chars'])+' букв/цифр;'
                     +' '+r['url'])
    lines+=['','## Светофор (без искусственного повышения)',
        '',
        '- **TZ-211 🔴:** оригинальные документы инвентаризированы,'
          ' но доступность *всех* официальных документов ещё не обеспечена.',
        '- **TZ-212 🔴:** даже Tagged=yes не подтверждает PDF/UA/ГОСТ'
          ' и структуру; нужна проверка и исправление каждого файла.',
        '- **TZ-213 🔴:** проверенный соответствующий оригиналу HTML'
          ' ещё не создан и не прошёл редакторское согласование.',
        '',
        'Вопросы музею: разрешено ли создавать доступные эквиваленты'
        ' официальных PDF из исходников; есть ли Word/архивные'
        ' редактируемые файлы; какой порядок вычитки и приёмки'
        ' юридических документов; какие PDF первоочередны?',
        '',
        'Приватные оригиналы не включены в Git и не изменены.',
        ]
    REPORT_MD.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print('AUDIT',{ 'documents':len(rows),'formats':dict(c),'pdf_tags':dict(t),
       'text_detected':ntext,'low_text':len(low)})
    print('REPORT',REPORT)
    print('SUMMARY',REPORT_MD)


if __name__=='__main__':
    data=json.loads(MANIFEST.read_text(encoding='utf-8'))
    result=inventory(data)
    publish(result)
