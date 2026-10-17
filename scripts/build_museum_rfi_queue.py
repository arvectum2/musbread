#!/usr/bin/env python3
"""Prepare UNSENT RFI workstream index from open requirements."""
import csv
from pathlib import Path
P=Path(__file__).resolve().parents[1]/'docs/tz-audit'
BANDS=[(1,15,'Сроки и интервью'),(16,71,'Айдентика и носители'),(72,113,'CMS и инфраструктура'),(114,146,'Музей и посещение'),(147,173,'Афиша и наука'),(174,241,'Контент и сервисы'),(242,267,'UX'),(268,277,'Внедрение'),(278,295,'Право'),(296,325,'Гарантия и передача')]
def load(file,enc,sep):
 with (P/file).open(encoding=enc,newline='') as f:return list(csv.DictReader(f,delimiter=sep))
def pack(k):
 n=int(k[3:]); names=[name for lo,hi,name in BANDS if lo<=n<=hi]
 if len(names)!=1:raise ValueError(k)
 return names[0]
def build():
 q=load('OPEN_CUSTOMER_QUESTIONS.csv','utf-8-sig',';')
 s=load('requirements.psv','utf-8','^')
 assert len(s)==325
 assert {r['ID'] for r in q}=={r['ID'] for r in s if r['Фактически готово']!='Да'}
 rows=[]
 for x in q:
  rows.append([x['ID'],pack(x['ID']),x['Приоритет'],x['Вопрос заказчику']])
 with (P/'CUSTOMER_RFI_QUEUE.csv').open('w',newline='',encoding='utf-8-sig') as f:
  w=csv.writer(f,delimiter=';',lineterminator='\n')
  w.writerow(['tz','group','priority','question'])
  w.writerows(rows)
 print('Prepared unsent questions',len(rows))
 return rows
if __name__=='__main__':build()
