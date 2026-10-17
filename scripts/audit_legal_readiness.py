#!/usr/bin/env python3
"""Preaward compliance EVIDENCE inventory, never a legal certification.

Does not call websites, transmit personal data, or approve any policy.
Public source code evidence is checked fail-closed; official approval cannot
be inferred from labels, links, source code or sample content.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = {
 "TZ-278": ("Общая применимость правовых актов", "Юрист музея утверждает список действующих обязательств"),
 "TZ-279": ("126-ФЗ «О связи»", "Сведения об операторе связи, провайдере хостинга и используемых услугах связи; юрист музея фиксирует применимость"),
 "TZ-280": ("149-ФЗ «Об информации, информационных технологиях и о защите информации»", "Владелец ИС и классификация информации, договор хостинга, журналы доступа, резервное копирование, ответственность и документированный план защиты"),
 "TZ-281": ("390-ФЗ «О безопасности»", "Заключение ответственного лица о сфере применения; не приравнивать сайт к субъекту полномочий государственных органов по умолчанию"),
 "TZ-288": ("Приказ Минкомсвязи 104 от 25.08.2009", "Определить, подпадает ли конкретная музейная система под сферу действия приказа (федеральные ГИС); подтвердить параметры надёжности, целостности, резервирования и ответственных"),
 "TZ-291": ("273-ФЗ «О противодействии коррупции»", "Утвердить исходный музейный антикоррупционный раздел и документы; проверить обязанности учреждения и ответственных без генерации политик"),
 "TZ-292": ("38-ФЗ «О рекламе»", "Определить, размещает ли музей реклама в юридическом смысле; при фактической рекламе утвердить роли, маркировку, ЕРИР/идентификатор и рекламодателя до включения блока"),
 "TZ-293": ("Закон РФ 2124-1 «О СМИ»", "Установить факт регистрации сайта как сетевого издания или отсутствие регистрации; не объявлять сайт СМИ по наличию новостей"),
 "TZ-282": ("152-ФЗ, персональные данные", "Подтвердить актуальность уже опубликованных документов музея и нужны ли новые формы"),
 "TZ-283": ("59-ФЗ, обращения граждан", "Подтвердить официальный канал и порядок обработки обращений, если он входит в проект"),
 "TZ-284": ("Закон 3612-1 о культуре", "Подтвердить список и редакции уже опубликованных документов"),
 "TZ-285": ("Приказ Минкультуры 277", "Согласовать список исходных файлов, способ переноса и ответственного за обновления"),
 "TZ-286": ("181-ФЗ, доступная среда", "Паспорт доступности, услуги сопровождения, достоверные входы/маршруты, UAT"),
 "TZ-287": ("ПП РФ 102 от 07.02.2026", "Подведомственность и сфера применения, скринридеры, клавиатура, экспертная приёмка"),
 "TZ-289": ("ГОСТ Р 52872-2019", "Полный аудит применимых критериев на рабочем сайте и с assistive tech"),
 "TZ-290": ("ГОСТ Р 70176-2022", "Оригиналы PDF, структурные теги, текст, язык, alt или проверенная доступная альтернатива"),
 "TZ-294": ("436-ФЗ, информация для детей", "Получить от музея правила редакционной проверки детских материалов, если нужны"),
}
SOURCES = {
 "TZ-278": "https://www.consultant.ru/document/cons_doc_LAW_179390/",
 "TZ-279": "https://www.consultant.ru/document/cons_doc_LAW_43224/b819c620a8c698de35861ad4c9d9696ee0c3ee7a/",
 "TZ-280": "https://www.consultant.ru/document/cons_doc_LAW_61798/0e9ec16b786dcbdaaa7f44abfc4a15e601d5be22/",
 "TZ-281": "https://www.consultant.ru/document/cons_doc_LAW_108546/27f9ddea0cccf9a6b90bb2cb8b545d436f18157b/",
 "TZ-288": "https://www.consultant.ru/document/cons_doc_LAW_92160/d33650469395d1c9beb4a8dd1094f9118f16cd23/",
 "TZ-291": "https://minjust.gov.ru/ru/documents/7864/",
 "TZ-292": "https://www.consultant.ru/document/cons_doc_LAW_58968/2c4537e4796f6ff8b2736ed1b0d4fef08e14458e/",
 "TZ-293": "https://www.consultant.ru/document/cons_doc_LAW_1511/36098bb636761bf8ffb8da67a5c769c0da48380a/",
 "TZ-282": "https://www.consultant.ru/document/cons_doc_LAW_61801/eeeebe22bf738fd65bb66b95cc278911ae2525ee/",
 "TZ-283": "https://rostransnadzor.gov.ru/news/16472",
 "TZ-284": "https://mintrud.gov.ru/docs/mintrud/analytics/65",
 "TZ-285": "https://minjust.consultant.ru/documents/14578?items=1&page=1",
 "TZ-286": "https://www.consultant.ru/document/cons_doc_LAW_8559/",
 "TZ-287": "https://www.consultant.ru/document/cons_doc_LAW_526205/",
 "TZ-289": "https://protect.gost.ru/gost/details/2d10ff38-d609-4dcc-899f-c18b77ac0b75",
 "TZ-290": "https://protect.gost.ru/gost/details/083ccfc7-6861-42d0-9861-011a7958fc71",
 "TZ-294": "https://www.consultant.ru/document/cons_doc_LAW_108808/",
}
# Screening matrix for the *museum* (subject to applicability/wording review).
# A URL to the OLD site's brochure never substitutes for signed official files.
DISCLOSURES = [
 ("identification", "Полное/краткое наименование, адрес и схема проезда", "museum-contacts"),
 ("foundation", "Дата создания, учредитель/ведомственная принадлежность", "museum-documents"),
 ("statute", "Устав и другие учредительные документы в проверенной версии", "museum-documents"),
 ("leadership", "Руководство, персонал и структура (применимый объём)", "museum-team"),
 ("services", "Сведения об услугах, графике, записи и условиях посещения", "plan-visit"),
 ("fees", "Стоимость платных услуг, льготы и правила возврата", "tickets-and-benefits"),
 ("finances", "Финансово-хозяйственные сведения/официальная отчётность", "museum-finance"),
 ("quality", "Независимая оценка качества услуг и результаты (при применимости)", "museum-documents"),
 ("accessibility", "Официальные сведения для маломобильных посетителей", "accessible-museum"),
 ("privacy", "Актуальная утверждённая политика обработки ПДн", "museum-privacy"),
 ("appeals", "Подтверждённый официальный канал обращений (при применимости)", "museum-feedback"),
 ("children", "Возрастная классификация и процесс модерации информации для детей", "children"),
]

def inspect(root: Path) -> dict:
    matrix_path = root / "docs/tz-audit/requirements.psv"
    with matrix_path.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream, delimiter="^"))
    by_id = {row["ID"]: row for row in rows}
    if len(rows) != 325 or len(by_id) != 325 or set(REFERENCE) - set(by_id):
        raise ValueError("Primary 325-clause tender evidence is missing or altered")
    integration = (root / "apps/web/src/integrations/public.ts").read_text(encoding="utf-8")
    published_path = root / "apps/web/src/data/published.json"
    snapshot = json.loads(published_path.read_text(encoding="utf-8"))
    ref = (root / "apps/web/src/data/museum-reference.ts").read_text(encoding="utf-8")
    # These inspect declared safe defaults; do not infer deployed state.
    feedback_disabled = "feedbackEnabled: false" in integration and "bookingEnabled: false" in integration
    analytics_disabled = "analyticsEnabled: false" in integration
    child_docs = [e for e in snapshot.get("entries", []) if e.get("type") == "document"]
    no_pii = all(all(k not in e for k in ("applicant_name", "email", "phone", "ip_address", "consent"))
                 for e in snapshot.get("entries", []))
    deploy_nginx = (root / "deploy/nginx").is_dir()
    no_pii_forms_enabled = feedback_disabled and analytics_disabled
    scope_by_law = {
        "TZ-279": (
            "static museum pages do not themselves prove the museum is a licensed telecom operator; "
            "review hosted telecommunications and provider contracts; applicability UNDECIDED"
        ),
        "TZ-280": (
            "verified local evidence: public static export, authenticated CMS separate from public, "
            "disabled PII/analytics by default, build CSP and private document access checks; "
            "server deployment, backup/recovery and threat model NOT accepted"
        ),
        "TZ-281": (
            "390-FZ covers the national/state/public security policy framework; no specific "
            "website-only technical compliance assertion follows from the title of the law; "
            "scope and accountable state institution must be confirmed"
        ),
        "TZ-288": ("order 104 scope requires a relevant federal government information system: "
            "museum web site is NOT ASSUMED eligible; existing manifest integrity, backup and "
            "deployment check scripts are partial engineering evidence, not commissioned hosting tests"),
        "TZ-291": ("official museum reference /protivodeystvie-korrupcii exists; unapproved site "
            "copies and institutional policies have NOT been synthesized; customer owns source files"),
        "TZ-292": ("no site-advertisement insertion or ERIR integration in public static prototype; "
            "ordinary museum exhibition notices are NOT AUTOMATICALLY advertising; ad status undecided"),
        "TZ-293": ("museum news section alone does NOT prove registration as network mass medium; "
            "registered network edition status is unknown, must be verified with customer"),

    }
    controls = [
        {"id": key,"source_clause":by_id[key]["Строки tz.txt"],
         "law": title,"verified_technical_scope":
         (scope_by_law[key] if key in scope_by_law else
         ("feedback/booking currently disabled; " if key in {"TZ-282","TZ-283"} and feedback_disabled else "")+
         ("no analytics by default; " if key == "TZ-282" and analytics_disabled else "")+
         ("published static snapshot excludes expected PII keys" if key == "TZ-282" and no_pii else
          "existing accessibility audit and CMS templates require real evidence" if key in {"TZ-286","TZ-287","TZ-289","TZ-290"} else
          "legal/document applicability requires customer verification")),
         "external_evidence_needed":pending,"reference_url":SOURCES[key],
         "compliance_approved":False,"approval_status":"AWAITING_MUSEUM_LEGAL_AND_UAT"}
        for key,(title,pending) in REFERENCE.items()
    ]
    disclosures=[]
    for key,label,slug in DISCLOSURES:
        internal=f"/guide/{slug}/"
        has_ref=f'"{slug}"' in ref
        disclosures.append({"key":key,"requested_evidence":label,"candidate_internal_route":internal,
                            "reference_navigation_exists":has_ref,
                            "official_signed_document_verified":False,
                            "accepted_by_museum":False,"status":"SOURCE_OR_APPROVAL_REQUIRED"})
    return {"report_type":"PREAWARD_NONLEGAL_NONCERTIFYING",
            "requirements_total":len(rows),"legal_ids_checked":len(controls),
            "legal_ready":False,"may_activate_appeals":False,
            "may_activate_real_pii_intake":False,"may_claim_pdf_ua_conformity":False,
            "signals":{"feedback_and_booking_disabled":feedback_disabled,
                       "analytics_disabled":analytics_disabled,
                       "no_expected_pii_in_snapshot":no_pii,
                       "published_document_records":len(child_docs),
                       "default_public_pii_intake_disabled":no_pii_forms_enabled,
                       "nginx_deployment_templates_present":deploy_nginx,
                       "telecom_operator_status_confirmed":False,
                       "state_security_law_applicability_approved":False},
            "legal_controls":controls,"disclosure_register":disclosures,
            "client_pending_total":len(controls)+len(disclosures),
            "warning":"Reference navigation is not verified publication. Legal approval is never inferred from filenames, links or passing tests."}

def markdown(report: dict) -> str:
    lines=["# Пакет юридической готовности TZ-278…294 — предконтрактный аудит", "",
           "**НЕ юридическое заключение, НЕ клиентская приёмка, НЕ разрешение включать формы/обработку ПДн.**", "",
           f"Проверено {report['legal_ids_checked']} пунктов ТЗ и {len(report['disclosure_register'])} категорий сведений. Юридически утверждено: **0**.", "",
           "## Обязательства и решения заказчика", "",
           "| ID | Нормативный блок | Нужно от музея | Юридическая приёмка |", "|---|---|---|---|"]
    for c in report["legal_controls"]:
        lines.append(f"| {c['id']} | {c['law']} | {c['external_evidence_needed']} | ❌ Нет |")
    lines += ["","## Ссылки на источники сведений (проверка актуальности музеем)","",
              "| Категория | Что запросить | Навигационная страница-ориентир | Подтверждено |", "|---|---|---|---|"]
    for row in report["disclosure_register"]:
        lines.append(f"| {row['key']} | {row['requested_evidence']} | `{row['candidate_internal_route']}` | ❌ Нет |")
    lines += ["","## Действующие ограничения безопасности", "",
              "- Реальных обращений граждан сайт **не принимает**: гостевая книга, электронная почта и демо-реестр не считаются юридически равнозначными официальному каналу.",
              "- Фактические формы с ФИО/телефонами, аналитика и бронирования не включаются до утверждения модели ПДн и инфраструктуры.",
              "- Документы в PDF без проверенных структурных тегов/языка/порядка чтения/alt не объявляются доступными согласно ГОСТ.",
              "- Для детских материалов требуется редакционная возрастная политика и подтверждение применимости 436-ФЗ.",
              "- Наличие пунктов меню, ссылки на старый сайт и чистый Playwright/axe-тест **не подтверждают** юридическое исполнение.", "",
              "## Практические образцы с сайтов музеев", ""]
    lines += [
      "- [Русский музей: уставные документы](https://rusmuseum.ru/pages/the-charter-of-the-museum/) — отдельный список оригиналов.",
      "- [Русский музей: правила билетов и возврата](https://rusmuseum.ru/pages/user-agreement/) — отдельная страница правил.",
      "- [Государственный музей истории Санкт-Петербурга: правила посещения](https://new.spbmuseum.ru/themuseum/visitors/pravila-posesh.php) — ссылка на утверждённый музейный оригинал.",
      "- [Музей хлеба: учредительные документы](https://muzei-xleb.ru/oficialnye-dokumenty-muzeya) — действующие исходники самого музея.",
      "- [Музей хлеба: две политики](https://muzei-xleb.ru/politika-konfidencialnosti-i-obrabotki-personalnyh-dannyh) — не писать новый текст.",
      "- [Музей хлеба: посещение и возврат](https://muzei-xleb.ru/ceny-i-usloviya-predostavleniya-uslug) — действующие положения.",
      "", "**Не делать:** не сочинять содержание правовых документов или процедуры на основании названия закона. Интерфейсный образец не является юридической экспертизой.",
      "Подробнее: `docs/tz-audit/MUSEUM_DOCUMENTS_BENCHMARK.md`.", "",
    ]
    return "\n".join(lines)

if __name__ == "__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--root",type=Path,default=ROOT)
    p.add_argument("--json",type=Path)
    p.add_argument("--markdown",type=Path)
    args=p.parse_args()
    report=inspect(args.root)
    if args.json:
        args.json.parent.mkdir(parents=True,exist_ok=True)
        args.json.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    if args.markdown:
        args.markdown.parent.mkdir(parents=True,exist_ok=True)
        args.markdown.write_text(markdown(report),encoding="utf-8")
    print("LEGAL_PREAWARD",report["legal_ids_checked"],"clauses;",len(report["disclosure_register"]),
          "disclosures; accepted=0; feedback-disabled=",report["signals"]["feedback_and_booking_disabled"])
