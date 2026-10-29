#!/usr/bin/env python3
"""Signed contract, OOZ and price annex page/line provenance (no signed bytes in Git)."""
from __future__ import annotations
import argparse
import difflib
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
FEATURE=ROOT/"specs/002-signed-contract"
MAP=FEATURE/"signed-line-map.json"
REPORT=FEATURE/"source-audit.md"
SIGNED=Path("/Volumes/ArvectumSSD/Arvectum/data/tenders/eis/0372200172326000015/signed_archive_20261023/signed_contract.pdf")
TXT=Path("/Volumes/ArvectumSSD/Arvectum/data/tenders/eis/0372200172326000015/tz.txt")
OOZ=ROOT/"docs/contract/OOZ_EIS_0372200172326000015.docx"
PDF_SHA="24616d4c274e7de1efe3bbe0b7c9605af9967f5a1e7087704a2db579c3e96ba8"
OOZ_SHA="3e029344d179742632d519d4e425e6f8e9f757ce4df23e0419aa4302d4068536"
SOURCE_SHA="92c4db2a3f47988f4fc4c96b5ae652baa3faaa62a772e55a167c7cbaafb67420"
REVIEWED_MAP_SHA="6f8c12edd13ada5e592f0da1c5b1725ba206baecd0996c6fc6003228bc57f0fd"
EXPECTED_LINES=1522
EXPECTED_CLAUSES=124   # populated after source-verified bootstrap
# Verified PDF table reflow on pp.19–20: headings leave the original
# word-order alignment but remain visibly present at the identified line.
MANUAL_TABLE_ANCHORS={"TZ-148":(19,46,"Экскурсии"),
                      "TZ-149":(19,51,"Детям"),
                      "TZ-150":(20,4,"Выставки")}

SECTION_RE=re.compile(r"^\s*(\d+(?:\.\d+){1,3})\.\s+(.+)")
SCOPE={**{p:"contract" for p in range(1,15)},**{p:"ooz" for p in range(15,27)},27:"rights_form",28:"price",29:"signatures"}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def get_pages() -> list[list[str]]:
    if not SIGNED.exists() or digest(SIGNED.read_bytes())!=PDF_SHA:
        raise ValueError("SIGNED PDF SHA-256 mismatch or signed private source missing")
    if not OOZ.exists() or digest(OOZ.read_bytes())!=OOZ_SHA:
        raise ValueError("Public OOZ copy differs from signed-source-matched competition OOZ")
    if not TXT.exists() or digest(TXT.read_bytes())!=SOURCE_SHA:
        raise ValueError("Private procurement TXT original SHA-256 mismatch")
    # Extract in memory: neither signed bytes nor bank details leave the private server.
    result=subprocess.run(["pdftotext","-layout",str(SIGNED),"-"],capture_output=True,check=True)
    pages=result.stdout.decode("utf-8").split("\f")
    if not pages[-1].strip():pages.pop()
    if len(pages)!=29:
        raise ValueError(f"Signed contract must have 29 actual pages: {len(pages)}")
    return [page.splitlines() for page in pages]


def tokens(line: str) -> list[str]:
    return re.findall(r"[а-яa-z0-9]+",unicodedata.normalize("NFKC",line.casefold()))


def source_token_map(source_lines: list[str]) -> tuple[list[str],list[int]]:
    all_words=[];indices=[]
    for n,line in enumerate(source_lines,1):
        if n<60 or n>465:continue
        for t in tokens(line):
            all_words.append(t);indices.append(n)
    return all_words,indices


def signed_token_map(pages: list[list[str]]) -> tuple[list[str],list[tuple[int,int]]]:
    words=[];indices=[]
    for pg in range(15,28):
        for line_num,line in enumerate(pages[pg-1],1):
            for tok in tokens(line):
                words.append(tok);indices.append((pg,line_num))
    return words,indices


def align_ooz(pages: list[list[str]]) -> dict:
    src=TXT.read_text(encoding="utf-8-sig").split("\n")
    source_words,source_loc=source_token_map(src)
    signed_words,signed_loc=signed_token_map(pages)
    matcher=difflib.SequenceMatcher(None,source_words,signed_words,autojunk=False)
    mapping={}
    hits=0
    for block in matcher.get_matching_blocks():
        for off in range(block.size):
            origin=source_loc[block.a+off]
            loc=signed_loc[block.b+off]
            mapping.setdefault(origin,set()).add(loc)
            hits+=1
    matched={str(n):[[pg,line] for pg,line in sorted(v)] for n,v in mapping.items()}
    return {"source_words":len(source_words),"signed_words":len(signed_words),
            "matched_words":hits,"original_lf_lines":485,"aligned_original_lines":len(matched),
            "line_to_signed_positions":matched}

def derive(pages: list[list[str]]) -> dict:
    all_lines=[]
    clauses=[]
    active=None
    for page_index,lines in enumerate(pages,1):
        scope=SCOPE[page_index]
        for line_number,line in enumerate(lines,1):
            if scope=="contract":
                match=SECTION_RE.match(line)
                if match and match[1].split(".")[0] in {str(x) for x in range(1,13)}:
                    active=match[1]
                    clauses.append({"clause":active,"page":page_index,"line":line_number,
                                    "line_sha256":digest(line.encode()),"scope":"contract"})
            all_lines.append({"page":page_index,"line":line_number,"scope":scope,
                              "sha256":digest(line.encode()),"blank":not bool(line.strip()),
                              "contract_clause":active if scope=="contract" else None})
    alignment=align_ooz(pages)
    load=importlib.util.spec_from_file_location("mb_tz",ROOT/"scripts/check_speckit_tz.py")
    m=importlib.util.module_from_spec(load);load.loader.exec_module(m)
    linked=[]
    for item in json.loads(m.MAP.read_text(encoding="utf-8"))["items"]:
        refs=item["physical_lines"]
        matched=sorted({tuple(pos) for ref in refs
                        for pos in alignment["line_to_signed_positions"].get(str(ref),[])})
        status="sequence_alignment" if matched else "unmatched"
        if not matched and item["id"] in MANUAL_TABLE_ANCHORS:
            pg,lin,anchor=MANUAL_TABLE_ANCHORS[item["id"]]
            if anchor not in pages[pg-1][lin-1]:
                raise ValueError(f"Human-checked PDF table heading moved: {item['id']}")
            matched=[(pg,lin)]
            status="human_verified_table_reflow"
        linked.append({"tz_id":item["id"],"original_clause":item["clause"],
                       "original_lf_lines":refs,"signed_pdf_positions":[list(p) for p in matched],
                       "signed_alignment_found":bool(matched),"alignment_method":status})
    raw="\n".join("\n".join(pg) for pg in pages)
    important=["0372200172326000015","07.12.2026","39 000","24 050,52","14 949,48",
               "21.10.2026","23.10.2026","Описание объекта закупки","Расчет цены Контракта"]
    for phrase in important:
        if phrase not in raw:
            raise ValueError(f"Expected signed contract anchor missing: {phrase}")
    return {"schema":1,"pdf_sha256":PDF_SHA,"ooz_docx_sha256":OOZ_SHA,
            "original_tz_sha256":SOURCE_SHA,"pages":len(pages),
            "signed_pages":{"main_contract":"1–14","ooz":"15–26",
                            "rights_transfer_form":"27","price_annex":"28",
                            "signature_receipt":"29"},
            "all_lines":all_lines,"contract_clauses":clauses,
            "original_ooz_alignment":{k:v for k,v in alignment.items() if k!="line_to_signed_positions"},
            "tz_atoms":linked}

def report(data: dict) -> str:
    stats=data["original_ooz_alignment"]
    n=sum(x["signed_alignment_found"] for x in data["tz_atoms"])
    return f"""# Подписанный контракт — построчный индекс и реестр обязательств

**Источник:** подписанный комплект ЕИС по закупке №0372200172326000015,
выгружен 30.10.2026 с MacBook в закрытый архив Mac mini.
**Подлинность электронных подписей средствами криптопровайдера отдельно не проверялась.**

- Подписанный PDF (закрытый): SHA-256 §{PDF_SHA}§.
- ООЗ DOCX (публичное приложение): SHA-256 §{OOZ_SHA}§.
- **29 страниц:** контракт 1–14, ООЗ 15–26, форма акта передачи прав 27,
  расчёт цены 28, информация о подписях 29.
- **{len(data["all_lines"])} физических строк PDF** с указанием страницы,
  номера строки, раздела и SHA-256 (включая пустые).
- **{len(data["contract_clauses"])} нумерованных пунктов** самого контракта
  с точными координатами и хешем первой строки.
- Сверка текста ООЗ: {stats["matched_words"]} из {stats["source_words"]} слов
  конкурсного оригинала ({stats["matched_words"]/stats["source_words"]*100:.2f}%).
  Расхождения при текстовом сопоставлении: вёрстка таблиц, нумерация страниц,
  переносы, оформленные подписи и реквизиты.
- **{n}/325** производных атомов ТЗ удалось привязать к строкам ООЗ внутри
  подписанного PDF; это не означает полного исполнения или юридической приёмки.

## Обязательства из основного договора

| Пункт и страница | Точное содержание по смыслу (не дословный нормативный текст) | Подтверждение |
|---|---|---|
| 1.2, с. 1 | ООЗ — приложение №1 и часть обязанностей | Дословный PDF/OOZ и hash |
| 1.3–1.4, с. 1 | Место услуг, окончание **07.12.2026 включительно** | Документы передачи и переписка |
| 2.4.1–2.4.4, с. 2 | Услуги, указания заказчика в рамках договора, отчёты и информация о ходе | Реальные документы передачи |
| 2.4.6, с. 2 | Конфиденциальность | Проверка хранения и доступа |
| 2.4.10–2.4.15, с. 2 | Авторские/исключительные права, согласования чужого контента | Лицензионный аудит, акт передачи прав |
| 3.1, с. 3 | Твёрдая цена **39 000,00 ₽** | Подписанный расчёт цены |
| 3.5–3.6, с. 3 | Нет аванса; расчёт после приёмки | ЕИС, документы оплаты |
| 3.12–3.13, с. 4 | Обеспечение исполнения | Подтверждающий документ (закрытый) |
| 5.1, с. 6 | Документ о приёмке в ЕИС не позднее **трёх рабочих дней** после срока услуг | Документ в ЕИС, дата |
| 5.4–5.5, с. 7 | Рассмотрение заказчиком в пределах **20 рабочих дней** по применимым процедурам | Дата поступления/ответа |
| 5.8, с. 8 | Исправление выявленных недостатков за свой счёт | Акты, дефектный список |
| 5.11, с. 8 | Передача предусмотренных контрактом документов | Комплект исходников, QA, инструкции |
| 6.1–6.5, с. 8 | Качество, лицензии, права на результаты | Проверка лицензий, безопасности |
| 12.1–12.2, с. 13 | Неотъемлемые приложения: ООЗ и расчёт цены | Наличие в PDF |

## Приложение №2 — расчёт цены (страница 28)

| Результат услуг | Количество | Цена, без НДС |
|---|---:|---:|
| Разработка сайта музея | 1 | 24 050,52 ₽ |
| Разработка элементов фирменного стиля | 1 | 14 949,48 ₽ |
| **Итого** | | **39 000,00 ₽** |

В договоре это уже согласованное распределение, а не наша новая оценка.
Покупка двух ВМ заказчиком не даёт оснований самостоятельно расширять цену
или объявлять работы по настройке дополнительным платным объёмом.

## Ограничения

1. У PDF и DOCX разные представления таблиц; побайтовое совпадение возможно
   между двумя DOCX (да, подтверждено), но не между текстом DOCX и PDF.
   Для спорного положения открывать полную страницу PDF, а не доверять краткому резюме.
2. Статус §325/325§ означает наличие привязки к подписанному PDF, а не то, что
   все атомарные инженерные трактовки юридически безошибочны.
3. Тексты и криптографические файлы подписанного договора, финансовые реквизиты
   и сертификаты остаются **в закрытом архиве**, а не в открытом Git.
4. Подписи датированы 21 и 23 октября 2026, как указано в PDF; независимая
   проверка цепочки доверия ГОСТ/ЕИС не проведена.
5. §--check§ в публичном CI проверяет индекс и структуру, но не может открыть
   подписанный PDF; §--verify-source§ на Mac mini проверяет настоящий PDF
   и все записанные строки и ссылки на ООЗ.

**Машинный реестр:** §signed-line-map.json§; юридическая первичность — за
подписанным PDF с приложениями, а не за этим производным отчётом.
""".replace("§",chr(96))

def validate(data: dict, pages: list[list[str]] | None) -> None:
    if data.get("schema")!=1 or data.get("pdf_sha256")!=PDF_SHA or data.get("ooz_docx_sha256")!=OOZ_SHA or data.get("original_tz_sha256")!=SOURCE_SHA or data.get("pages")!=29:
        raise ValueError("Signed source identity does not match pinned contract")
    rows=data.get("all_lines",[])
    if len(rows)!=EXPECTED_LINES:raise ValueError("Signed document line count changed")
    last=(0,0)
    for entry in rows:
        pg,no=entry["page"],entry["line"]
        if not 1<=pg<=29 or (pg,no)<=last or entry["scope"]!=SCOPE[pg]:
            raise ValueError("Signed line sequence/scope invalid")
        if not re.fullmatch("[a-f0-9]{64}",entry["sha256"]):
            raise ValueError("Malformed signed line hash")
        if pages is not None:
            line=pages[pg-1][no-1]
            if digest(line.encode())!=entry["sha256"] or (not line.strip())!=entry["blank"]:
                raise ValueError(f"Signed PDF text line diverged: p{pg} line{no}")
        last=(pg,no)
    if len(data.get("contract_clauses",[]))!=EXPECTED_CLAUSES:
        raise ValueError("Incomplete contract clause index")
    if len(data.get("tz_atoms",[]))!=325:
        raise ValueError("Signed annex lost 325 TZ atoms")
    for n,entry in enumerate(data["tz_atoms"],1):
        if entry["tz_id"]!=f"TZ-{n:03d}":raise ValueError("Signed atom ordering wrong")
        if not entry["signed_alignment_found"] or not entry["signed_pdf_positions"]:
            raise ValueError(f"Signed appendix mapping missing: {entry['tz_id']}")
        for pg,lin in entry["signed_pdf_positions"]:
            if not 15<=pg<=27 or not 1<=lin<=len(pages[pg-1] if pages is not None else [None]*150):
                raise ValueError("Signed annex points out of bounds")
    aligned=data["original_ooz_alignment"]
    if aligned["matched_words"]/aligned["source_words"] < .97:
        raise ValueError("Signed OOZ differs substantively from original")


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    action=parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--bootstrap",action="store_true")
    action.add_argument("--verify-source",action="store_true")
    action.add_argument("--check",action="store_true")
    args=parser.parse_args()
    try:
        if args.bootstrap:
            if MAP.exists():raise ValueError("Signed baseline already exists; do not overwrite")
            pages=get_pages()
            data=derive(pages)
            validate(data,pages)
            MAP.parent.mkdir(exist_ok=True,parents=True)
            MAP.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
            REPORT.write_text(report(data),encoding="utf-8")
        else:
            if digest(MAP.read_bytes())!=REVIEWED_MAP_SHA:
                raise ValueError("Review-locked signed PDF map changed without source review")
            data=json.loads(MAP.read_text(encoding="utf-8"))
            pages=get_pages() if args.verify_source else None
            validate(data,pages)
            if pages is not None:
                expected=derive(pages)
                if data!=expected:raise ValueError("Signed appendix alignment has changed")
            if REPORT.read_text(encoding="utf-8")!=report(data):
                raise ValueError("Signed contract report is out of sync")
        typ="SIGNED PDF VERIFIED" if args.bootstrap or args.verify_source else "CI STRUCTURE ONLY"
        print(f"Signed Spec Kit {typ}: 29 pages, {len(data['all_lines'])} lines, "
              f"{len(data['contract_clauses'])} clauses, "
              f"{sum(a['signed_alignment_found'] for a in data['tz_atoms'])}/325 aligned TZ")
        return 0
    except (ValueError,KeyError,OSError,subprocess.CalledProcessError) as exc:
        print("Signed Spec Kit FAIL:",str(exc),file=sys.stderr)
        return 1


if __name__=="__main__":
    raise SystemExit(main())
