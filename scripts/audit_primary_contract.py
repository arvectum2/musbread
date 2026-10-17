#!/usr/bin/env python3
"""Verify original EIS Word extracts line-by-line, map 325 TZ and contract.

Originals and complete line text stay OUTSIDE the public repository.
The two entire 485/837 line indexes are written to ignored .local_archive.
Derived clause references, discrepancies and questions may be committed.
"""
from __future__ import annotations

import argparse
import csv
from collections import Counter,defaultdict
from difflib import SequenceMatcher
import hashlib
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/"docs/tz-audit/requirements.psv"
OUT=ROOT/"docs/tz-audit"
PRIVATE=ROOT/".local_archive/primary-source-audit"
SHA={
"tz.docx":"3e029344d179742632d519d4e425e6f8e9f757ce4df23e0419aa4302d4068536",
"contract.doc":"9294908cc3aec0bda85c84d41cd19b80fe1e5ddebd1b386b4830466d64eca091",
"tz.txt":"92c4db2a3f47988f4fc4c96b5ae652baa3faaa62a772e55a167c7cbaafb67420",
"contract.txt":"2ff022cbfcf18446a6b3db1c60ffd2d3d30d4967a00039a8b7cfb3fa5844e350",
}
PAT=re.compile(r"^\s*(\d+(?:\.\d+){1,4})\.?\s+(?=\S)")

# Each discrepancy is grounded in an EXACT physical source line or contract
# cross-reference. A proposed question is not a unilateral contract edit.
ISSUES=[
("D01","КРИТИЧНО","Различаются ИКЗ в преамбуле контракта и пункте 1.1 ТЗ",
 "К:59; ТЗ:61","Какой ИКЗ верный для подписываемого контракта?","Реквизиты/закупка"),
("D02","ВЫСОКО","Контракт 4.1 отсылает к 1.6 ТЗ (цель), срок находится в 1.5",
 "К:151; ТЗ:65–66","Исправите ссылку пункта 4.1 на 1.5 ТЗ?","Сроки"),
("D03","ВЫСОКО","В п. 1.3 контракта место только очное; ТЗ 1.4 допускает удалённо по согласованию",
 "К:69; ТЗ:64","Можно письменно закрепить удалённую работу, кроме обязательного очного интервью?","Место выполнения"),
("D04","КРИТИЧНО","Оказание до 07.12; EIS-документ до 3 рабочих дней после; приёмка до 20 рабочих дней, но действие контракта до 31.12",
 "К:70,152,159,173,225; ТЗ:65","Как согласуем приёмку, оформление акта и оплату при выходе срока проверки за 31.12?","Сроки приёмки"),
("D05","ВЫСОКО","В пункте 5.4 экспертиза ошибочно отсылается к самому пункту 5.4; документы — к 5.2 вместо 5.1.3",
 "К:162–166,168,173","Уточните ссылки в п. 5.4 на экспертизу 5.3 и приложения 5.1.3?","Техника договора"),
("D06","ВЫСОКО","ОКТМО отличается внутри договора: назначение платежа и реквизиты сторон",
 "К:148,297","Какой ОКТМО считать правильным для документов и платежей?","Реквизиты"),
("D07","КРИТИЧНО","Передача всех исключительных прав на созданные И ИСПОЛЬЗУЕМЫЕ результаты конфликтует с возможной недоступностью исключительных прав на сторонние библиотеки/фото",
 "К:100–104,194–198; ТЗ:380,388–390","Можно письменно разграничить передаваемый авторский результат и сторонние OSS/лицензии?","Интеллектуальные права"),
("D08","ВЫСОКО","Нет аванса; вся оплата после приёмки, платёж до 7 рабочих дней после документов",
 "К:112–125,119,124","Подтвердите отсутствие этапных платежей и окончательную процедуру оплаты?","Денежный поток"),
("D09","ВЫСОКО","Гарантия 12 месяцев; реакция до 24 ч, сложный дефект максимум 5 рабочих дней",
 "ТЗ:71,352–361; К:193–199","Какой официальный канал поддержки и кто фиксирует момент поступления обращения?","Гарантия"),
("D10","ВЫСОКО","Пять рабочих дней просрочки после конца работ — основание одностороннего отказа",
 "К:228–236","Согласуем контрольные даты и процедуру фиксирования задержек согласования?","Расторжение"),
("D11","ВЫСОКО","Три концепции после обязательного ОЧНОГО интервью, не меньше пяти PDF-страниц каждая, презентация через 2 рабочих дня",
 "ТЗ:76–79,315–319","Когда очное интервью и окно презентации трёх концепций?","Календарь"),
("D12","ВЫСОКО","В договоре нет финальной цены, НДС, исполнителя и обеспечения — это шаблон до заключения",
 "К:58–63,112,127,307–333,764–790","Когда будет подписанный проект с заполненной ценой, НДС и обеспечением?","Заключение"),
("D13","ВЫСОКО","Форма приложений требует счёт, акт услуг, акт передачи исключительных прав и ЭП в ЕИС",
 "К:159–166,274,724–757; ТЗ:449–483","Кто примет и согласует комплект актов, реквизиты и способ подписания оригиналов?","Документы сдачи"),
("D14","ВЫСОКО","Два условных вида услуг в приложении 2 (сайт и фирменный стиль); оплата указана после полного завершения",
 "К:124,764–792","Будут ли два результата отдельно проверяться при единой окончательной оплате?","Этапы/цена"),
("D15","ВЫСОКО","Уведомить о любом соисполнителе нужно в течение 3 дней; за него отвечает исполнитель",
 "К:99; К:212","Кого считаем соисполнителем и куда направлять уведомление о нём?","Соисполнители"),
("D16","ВЫСОКО","Передать исходники, ключи, бумажный комплект и материалы на съёмном носителе, сайт в Интернете",
 "ТЗ:370–385,303–325","Кто уполномочен принять сервер, исходники, ключи, носитель и бумаги?","Передача"),
("D17","ВЫСОКО","Нужны утверждённые тексты и права на музейные фото, шрифты, дизайны, документы",
 "ТЗ:75–126,236–247,380; К:100–104","Кто и в какие сроки предоставит исходники с подтверждением прав?","Контент/права"),
("D18","СРЕДНЕ","ТЗ 2.2.3.9.2: заказчик отвечает на запросы согласования за 2 рабочих дня",
 "ТЗ:323–330","Какой официальный e-mail и кто замещает согласующего при отсутствии ответа?","Согласования"),
("D19","ВЫСОКО","В цену входит всё, включая пошлины, налоги, транспорт и иные расходы",
 "К:112–114; ТЗ:64,71–126","Подтвердите обязательные очные выезды и возможность ВКС после интервью?","Себестоимость"),
("D20","ВЫСОКО","Штраф за ненадлежащее исполнение каждого вида, отдельно за обязанности без цены",
 "К:207–219,812–823","Уточните подсчёт штрафов для двух позиций расчёта цены?","Ответственность"),
("D21","ВЫСОКО","CMS, билеты, карты, доступы и реальное размещение требуют решений на стороне заказчика",
 "ТЗ:247–250,314–322,364–385","Когда будут API/домен/хостинг/ответственные и тестовый доступ?","Внешние доступы"),
("D22","ВЫСОКО","Формы передачи прав предусматривают два подлинных экземпляра, но контракт подписывается УКЭП",
 "К:274,724–757; ТЗ:461–465","Два бумажных подлинника акта нужны дополнительно к электронному ЕИС-акту?","Подписание"),
("D23","СРЕДНЕ","Замечания заказчика исправляются за счёт исполнителя в назначенный заказчиком срок",
 "ТЗ:323–330; К:91,183–189","Как оформлять перечень замечаний и разумные сроки без изменения объёма ТЗ?","Приёмка"),
("D24","ВЫСОКО","Реальная гарантийная эксплуатация зависит от хостинга и прав администрирования",
 "ТЗ:352–361; К:194–199","Кто отвечает за обновления сервера и восстановление резервных копий?","Инфраструктура"),
("D25","СРЕДНЕ","Правовой режим результатов для регистрации бренда и шрифтов требует чистой цепочки прав",
 "ТЗ:83,85–91,388–390; К:100–104","Кто согласует проверку товарного знака и лицензии исходных графических файлов?","Бренд/регистрация"),
]

def normalized(text:str)->str:return re.sub(r"\W+","",text.lower(),flags=re.U)
def read_lines(path:Path)->list[str]:
 raw=path.read_text(encoding="utf-8").split("\n")
 if raw[-1]=="":raw.pop()
 return raw
def source_data(folder:Path)->dict[str,list[str]]:
 for name,sha in SHA.items():
  file=folder/name
  if not file.exists():raise FileNotFoundError(file)
  got=hashlib.sha256(file.read_bytes()).hexdigest()
  if sha!=got:raise ValueError(f"Original changed since verified snapshot: {name} {got}")
 tz=read_lines(folder/"tz.txt");contract=read_lines(folder/"contract.txt")
 if (len(tz),len(contract))!=(485,837):raise ValueError("Source physical line count unexpectedly changed")
 return {"tz":tz,"contract":contract}

def tz_line_refs()->dict[int,list[str]]:
 with SOURCE.open(encoding="utf-8",newline="") as f:rows=list(csv.DictReader(f,delimiter="^"))
 if len(rows)!=325:raise ValueError("325 canonical clauses required")
 mapped=defaultdict(list)
 for r in rows:
  for a,b in re.findall(r"(\d+)(?:-(\d+))?",r["Строки tz.txt"]):
   for line in range(int(a),int(b or a)+1):mapped[line].append(r["ID"])
 return mapped

def audit(folder:Path)->dict:
 data=source_data(folder);tz=data["tz"];contract=data["contract"]
 refs=tz_line_refs()
 # Exactly equal main annex, including table/heading text, not merely similar.
 original=[normalized(t) for t in tz[59:396] if len(normalized(t))>=8]
 annex=[normalized(t) for t in contract[365:702] if len(normalized(t))>=8]
 if len(original)!=317 or original!=annex:raise AssertionError("TZ and contract annex are not identical")
 # Physical line register is deliberately PRIVATE, under .gitignored local archive.
 PRIVATE.mkdir(parents=True,exist_ok=True)
 with (PRIVATE/"tz_485_line_audit.csv").open("w",newline="",encoding="utf-8-sig") as f:
  writer=csv.writer(f,delimiter=";",lineterminator="\n")
  writer.writerow(["Исходная строка","Текст первоисточника (локально)","Связанные TZ","Классификация"])
  for no,line in enumerate(tz,1):
   has=bool(normalized(line));ref=refs.get(no,[])
   kind=("ПУСТАЯ" if not has else "325-МАТРИЦА" if ref else
        "КОНТЕКСТ/ЗАГОЛОВОК/ОФОРМЛЕНИЕ" if no!=31 else "УСЛОВИЕ ДОПУСКА СМП")
   writer.writerow([no,line,",".join(ref),kind])
 ids=[];clause_starts=[]
 for no,line in enumerate(contract[:359],1):
  m=PAT.match(line)
  if m:clause_starts.append((no,m.group(1)))
 with (PRIVATE/"contract_837_line_audit.csv").open("w",newline="",encoding="utf-8-sig") as f:
  writer=csv.writer(f,delimiter=";",lineterminator="\n")
  writer.writerow(["Исходная строка","Текст первоисточника (локально)","Раздел/пункт","Связанные TZ","Классификация"])
  active=""
  for no,line in enumerate(contract,1):
   if no<=359:
    m=PAT.match(line)
    if m:active=m.group(1)
    category="КОНТРАКТ"
   elif no<=702:
    category="ТЗ В ПРИЛОЖЕНИИ №1"
    active="ТЗ:"+str(no-306)
   elif no<=763:category="АКТ ИСКЛЮЧИТЕЛЬНЫХ ПРАВ"
   elif no<=806:category="ПРИЛОЖЕНИЕ №2, РАСЧЁТ ЦЕНЫ"
   else:category="СНОСКИ К ДОГОВОРУ"
   writer.writerow([no,line,active,
      ",".join(refs.get(no-306,[])) if 366<=no<=702 else "",
      category if line.strip() else "ПУСТАЯ"])
 # Rigorous raw-value consistency checks.
 contract_ikz=re.search(r"ИКЗ\s+(\d{30,40})",contract[58]).group(1)
 tz_ikz=re.search(r"(\d{30,40})",tz[60]).group(1)
 if contract_ikz==tz_ikz:raise AssertionError("Expected IKZ mismatch no longer present")
 octmo1=re.search(r"ОКТМО\s*[–-]\s*(\d+)",contract[147]).group(1)
 octmo2=re.search(r"ОКТМО\s+(\d+)",contract[296]).group(1)
 if octmo1==octmo2:raise AssertionError("Expected OKTMO mismatch no longer present")
 if "п. 1.6." not in contract[150] or "1.5." not in tz[64]:
  raise AssertionError("Expected deadline cross-reference mismatch missing")
 if "пунктом 5.4." not in contract[172]:
  raise AssertionError("Expected erroneous internal examination cross-reference missing")
 # Build all numbered clauses, even customer rights, unchanged normative boilerplate.
 clauses=[]
 with (OUT/"CONTRACT_CLAUSE_MAP.csv").open("w",newline="",encoding="utf-8-sig") as f:
  fields=["Пункт договора","Строки оригинала","О чём пункт (первые слова)","Тема","Статус аудита","Связанные вопросы риска","Вопрос для согласования"]
  writer=csv.DictWriter(f,fieldnames=fields,delimiter=";",lineterminator="\n");writer.writeheader()
  for idx,(start,num) in enumerate(clause_starts):
   end=(clause_starts[idx+1][0]-1 if idx+1<len(clause_starts) else 359)
   first=contract[start-1].strip()
   summary=re.sub(r"\s+"," ",PAT.sub("",first,1)).strip()[:135]
   chapter=num.split(".")[0]
   theme={
    "1":"Предмет и срок","2":"Обязанности и IP","3":"Цена и обеспечение",
    "4":"Срок действия","5":"Приёмка через ЕИС","6":"Гарантии",
    "7":"Штрафы и риски","8":"Расторжение","9":"Форс-мажор",
    "11":"Коммуникации и споры","12":"Приложения"
   }.get(chapter,"Прочее")
   risk_ids=[
    issue[0] for issue in ISSUES if
    # High-level references are not automatic citations: map to immediate contract source line.
    re.search(r"(?:^|К:|,|–)"+re.escape(str(start))+r"(?:,|;|$)",issue[3])
   ]
   if num in ("1.4","4.1"):risk_ids.append("D02")
   if num=="2.4.15":risk_ids.append("D07")
   if num in ("5.4","5.5"):risk_ids.append("D04")
   if num in ("5.1","3.6"):risk_ids.append("D08")
   if num in ("7.3.2","7.3.3","7.3.4"):risk_ids.append("D20")
   status="СВЕРЕН; ИСПОЛНЕНИЕ ПОСЛЕ ПОДПИСАНИЯ" if chapter not in ("2","5","6","7","8") else "СВЕРЕН; ПРАВОВОЕ/ОПЕРАЦИОННОЕ ИСПОЛНЕНИЕ ОТКРЫТО"
   question={
     "1":"Какой график работ и место выполнения будут закреплены?",
     "2":"Кто подтвердит ответственность и предоставит нужные согласования?",
     "3":"Какая цена/обеспечение/оплата будут в подписанной редакции?",
     "4":"Какой срок применяем при оформлении приёмки?",
     "5":"Кто оформит документы ЕИС, акты и экспертизу в срок?",
     "6":"Какие ответственные и доказательства гарантий будут согласованы?",
     "7":"Как считаются штрафы и фиксируются случаи нарушений?",
     "8":"Как уведомляют и фиксируют основания одностороннего отказа?",
     "9":"Какой канал для уведомления о форс-мажоре?",
     "11":"Какой канал и кто отвечает за договорную переписку?",
     "12":"Какие приложения и версии будут подписаны?"
   }.get(chapter,"Кто согласует обязательства?")
   clauses.append(dict(zip(fields,[num,f"{start}–{end}",summary,theme,status,", ".join(sorted(set(risk_ids))),question])))
  # Section 10 has no numbered subparagraphs, still an entire enforceable block.
  clauses.append(dict(zip(fields,["10","254–259","Антикоррупционные обязательства сторон","Антикоррупция",
     "СВЕРЕН; ОБЯЗАТЕЛЬСТВО ПОСЛЕ ПОДПИСАНИЯ","D17","Кто контролирует соблюдение антикоррупционных правил?"])))
  for row in clauses:writer.writerow(row)
 issues_path=OUT/"CONTRACT_DISCREPANCIES_AND_RISKS.csv"
 with issues_path.open("w",newline="",encoding="utf-8-sig") as f:
  w=csv.writer(f,delimiter=";",lineterminator="\n")
  w.writerow(["ID","Риск","Вывод первичной сверки","Строки источника","Лаконичный вопрос заказчику","Тема"])
  w.writerows(ISSUES)
 stats={
  "tz_source_lines":len(tz),"contract_source_lines":len(contract),
  "tz_nonempty_lines":sum(bool(normalized(x)) for x in tz),
  "tz_nonempty_covered_by_atomic_rows":sum(bool(normalized(x)) and i in refs for i,x in enumerate(tz,1)),
  "tz_unmapped_nonempty":sum(bool(normalized(x)) and i not in refs for i,x in enumerate(tz,1)),
  "contract_clauses":len(clauses),"tz_contract_annex_exact_lines":317,
  "discrepancies_and_risks":len(ISSUES),
  "contract_ikz":contract_ikz,"tz_ikz":tz_ikz,
  "contract_octmo_payment":octmo1,"contract_octmo_requisites":octmo2,
  "source_sha256":{key:value for key,value in SHA.items()},
 }
 (PRIVATE/"verification.json").write_text(json.dumps(stats,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 return stats

def main():
 p=argparse.ArgumentParser()
 p.add_argument("--source-dir",required=True,type=Path)
 args=p.parse_args()
 print("PRIMARY_EIS_SOURCE_AUDIT",json.dumps(audit(args.source_dir),ensure_ascii=False))

if __name__=="__main__":main()
