#!/usr/bin/env python3
"""Inventory the official-site originals and CMS drafts without accessing the network."""
import argparse,csv,json,sqlite3
from collections import Counter
from hashlib import sha256
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser()
 p.add_argument('--snapshot',type=Path,default=ROOT/'apps/web/src/data/official-page-snapshots.json')
 p.add_argument('--archive',type=Path,default=ROOT/'.local_archive/official-site-originals/manifest.json')
 p.add_argument('--database',type=Path,default=ROOT/'apps/cms/database/database.sqlite')
 a=p.parse_args()
 src=json.loads(a.snapshot.read_text())
 arc=json.loads(a.archive.read_text())
 assert src['source']==arc['source']=='https://muzei-xleb.ru'
 original={f['url']:f for f in arc['files']}
 with sqlite3.connect(f'file:{a.database}?mode=ro',uri=True) as db:
  cms={x[0]:x[1] for x in db.execute('select d.sha256,e.slug from museum_documents d join museum_entries e on e.id=d.museum_entry_id')}
 docs=[]
 for page in src['pages']:
  for doc in page['document_links']:
   u=doc['url']
   assert u.startswith('https://muzei-xleb.ru/sites/default/files/')
   f=original.get(u)
   if f:
    loc=a.archive.parent/f['local_name']
    assert loc.stat().st_size==f['size_bytes'] and sha256(loc.read_bytes()).hexdigest()==f['sha256']
   docs.append(dict(section=page['path'],document=doc['label'],url=u,extension=u.rsplit('.',1)[-1],
                    snapshot_utc=page['captured_utc'],sha256=f['sha256'] if f else '',
                    original_bytes=f['size_bytes'] if f else '',
                    original_cached='yes' if f else 'no',
                    private_cms_entry=cms.get(f['sha256'],'') if f else '',
                    accessibility_reviewed='unknown'))
 assert len(docs)==len({x['url'] for x in docs})
 output=ROOT/'docs/tz-audit/OFFICIAL_MUSEUM_DOCUMENT_INVENTORY_20261017.csv'
 with output.open('w',encoding='utf-8-sig',newline='') as fd:
  writer=csv.DictWriter(fd,fieldnames=list(docs[0]),delimiter=';',lineterminator='\n')
  writer.writeheader();writer.writerows(docs)
 counts=Counter(x['section'] for x in docs)
 cached=Counter(x['section'] for x in docs if x['original_cached']=='yes')
 attached=Counter(x['section'] for x in docs if x['private_cms_entry'])
 lines=['# Ведомость официальных документов музея хлеба, 17.10.2026','',
        'Источник: дата-снимок действующего сайта muzei-xleb.ru, полученный через Mac mini.',
        'Оригиналы сохранены в приватном архиве ArvectumSSD; в публичный Git попала только ведомость.',
        'Файловых ссылок: '+str(len(docs))+'. Проверенных оригиналов в архиве: '+str(len(original))+'.',
        'Ссылка на первоисточник не равно доступная версия документа для экранного диктора.','',
        '| Исходный раздел | Ссылок | Оригиналы с SHA-256 | Из оригиналов привязано к CMS |',
        '|---|---:|---:|---:|']
 for sec,n in counts.items():
  lines.append('| '+sec+' | '+str(n)+' | '+str(cached[sec])+' | '+str(attached[sec])+' |')
 lines+=['','Сжатая копия одной политики ПДн **не считается неизменённым оригиналом**. '
  'Оригинал хранится отдельно, в CMS у сжатой копии новый SHA-256 и отдельная пометка.',
  'Восьми-страничное положение о возврате и исходный бланк DOCX размещены в CMS как черновые вложения.',
  'Полный список с URL, названием, размером и SHA-256: OFFICIAL_MUSEUM_DOCUMENT_INVENTORY_20261017.csv.','','Не скачаны:']
 missing=[x for x in docs if x['original_cached']=='no']
 lines += ['- '+x['document']+' — '+x['url'] for x in missing] if missing else ['- Нет. Все исходные файлы сохранены в закрытом архиве (проверка доступности и публикация ещё открыты).']
 output.with_suffix('.md').write_text('\n'.join(lines)+'\n')
 print('SOURCE LINKS',len(docs),'CACHED',len(original),'NOT CACHED',len(missing),'CMS SHA RECORDS',len(cms))
if __name__=='__main__':main()
