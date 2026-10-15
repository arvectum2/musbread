#!/usr/bin/env python3
"""Render the source-traced requirements register for tender MusBread."""
from __future__ import annotations
import csv
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "docs/tz-audit/requirements.psv"
OUTPUT = ROOT / "docs/tz-audit/TZ_FULL_MATRIX.md"
CSV_OUTPUT = ROOT / "docs/tz-audit/TZ_FULL_MATRIX.csv"
GROUPS = [
    (1, 16, "Исходные условия, очное интервью и концепции"),
    (17, 71, "Фирменный стиль, все носители и исходники"),
    (72, 113, "Архитектура, права доступа, безопасность, SLA"),
    (114, 172, "Полное дерево сайта по ТЗ, шапка и футер"),
    (173, 213, "Навигация, SEO, контент, интеграции и доступность"),
    (214, 262, "Технологический стек, UI, UX и прототипирование"),
    (263, 325, "Согласования, нормативные акты, гарантия, сдача прав"),
]

def read_rows():
    with INPUT.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="^"))
    if len(rows) < 300:
        raise ValueError("Unfinished requirements register")
    if [int(r["ID"][3:]) for r in rows] != list(range(1, len(rows) + 1)):
        raise ValueError("ID sequence is incomplete")
    for r in rows:
        if any(not v or not v.strip() for v in r.values()) or None in r:
            raise ValueError("Missing column: " + r.get("ID", "unknown"))
        if r["Учли в плане"] not in ("Да", "Частично", "Нет"):
            raise ValueError("Invalid accounting status")
        if r["Фактически готово"] not in ("Да", "Частично", "Нет"):
            raise ValueError("Invalid implementation status")
        if r["Приоритет"] not in ("P0", "P1", "P2"):
            raise ValueError("Invalid priority")
        for span in r["Строки tz.txt"].split(","):
            ends = [int(x) for x in span.strip().split("-")]
            if len(ends) > 2 or not 1 <= min(ends) <= max(ends) <= 485:
                raise ValueError("Invalid original source line reference")
    return rows

def e(text):
    return str(text).replace("|", "/").replace("\n", " ")

def table(items):
    result = [
        "| ID | Оригинал ТЗ | Требование | Учли? | Готово? | Что есть | Что осталось | От музея | P |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in items:
        fields = [
            r["ID"], r["Пункт ТЗ"] + " (стр. " + r["Строки tz.txt"] + ")",
            r["Атомарное обязательство"], r["Учли в плане"], r["Фактически готово"],
            r["Чекпоинт/доказательство"], r["Осталось выполнить"],
            r["Нужно от заказчика"], r["Приоритет"],
        ]
        result.append("| " + " | ".join(map(e, fields)) + " |")
    return result

def main():
    rows = read_rows()
    plan = Counter(r["Учли в плане"] for r in rows)
    done = Counter(r["Фактически готово"] for r in rows)
    gap = [r for r in rows if r["Учли в плане"] == "Нет"]
    p0 = sum(r["Приоритет"] == "P0" for r in rows)
    document = [
        "# MusBread — построчная трассировка первичного ТЗ №0372200172326000015",
        "",
        "**Аудит 15.10.2026 по версии кода 68f16c9.** Исходник — скачанное с ЕИС",
        "Описание объекта закупки (приложение 3 к извещению), оригинал tz.docx и",
        "текстовый экспорт tz.txt на Mac mini. DOCX и TXT проверены: в обоих",
        "по 4 957 буквенно-цифровых токенов, потерянных типов токенов нет;",
        "в DOCX имеются три таблицы. Номера строк ниже относятся к локальному tz.txt.",
        "",
        "Одна строка аудита соответствует **одному самостоятельно проверяемому требованию**.",
        "Одно сложное предложение ТЗ может быть разбито на десять требований.",
        "Учли: Да = есть в старой карте или коде, Частично = только общей фразой,",
        "Нет = требование не было самостоятельно отслежено.",
        "Готово: Да = реально реализовано и проверено в прототипе;",
        "Частично = есть лишь часть или каркас; Нет = требуемого результата пока нет.",
        "Ни один статус готовности НЕ означает официальную приёмку музеем.",
        "Приоритет P0 = возможный блокер приёмки; P1 = обязательное к сдаче;",
        "P2 = отдельный мелкий носитель или подпункт.",
        "",
        "## Сводка",
        "",
        "| Статус | Атомарных требований |",
        "|---|---:|",
        f"| Всего | **{len(rows)}** |",
        f"| Учли Да / Частично / Нет | {plan['Да']} / {plan['Частично']} / **{plan['Нет']}** |",
        f"| Готово Да / Частично / Нет | {done['Да']} / {done['Частично']} / **{done['Нет']}** |",
        f"| Приоритет P0 | **{p0}** |",
        "",
        "**Не вычислять процент выполнения контракта** делением этих чисел:",
        "строки неодинаковы по трудоёмкости, а дизайн и инфраструктура ждут согласования.",
        "Перечень нормативных документов приведён как в первичном ТЗ;",
        "действительность и применимость норм требуют отдельной юридической проверки.",
        "",
        "## Полная матрица",
        "",
    ]
    for start, end, title in GROUPS:
        document += [f"### {title} — TZ-{start:03d}…TZ-{end:03d}", ""]
        document.extend(table(rows[start-1:end]))
        document.append("")
    document += [
        "## Что не было явно учтено ранее",
        "",
        "Ниже все условия с отметкой Учли = Нет — ни одно не теряется.",
        "Остальные условия, учтённые только частично, находятся в основных таблицах.",
        "",
    ]
    document.extend(table(gap))
    document += [
        "",
        "## Практическое правило закрытия",
        "",
        "Пока нет результатов конкурса — самостоятельные технические задачи:",
        "полная иерархия сайта, CMS разделы/ACL/формы, глобальный поиск,",
        "sitemap/robots, SCSS, чистый rem/em, регламент метрик скорости/ширины,",
        "каркас обязательного футера и правовых страниц (без вымышленных юридических текстов).",
        "",
        "После интервью — три РЕАЛЬНЫЕ концепции, фирменные носители и исходники",
        "во всех перечисленных размерах и форматах. PDF-каркасы ими не являются.",
        "",
        "После предоставления серверов и API — TLS, канал между контурами,",
        "билеты и заявки, резервирование, мониторинг, пентест, нагрузка, полная",
        "кроссбраузерность, два UX-раунда, утверждённое наполнение.",
        "",
        "Только после приёмки — реальные носители, парольный комплект по защищённому",
        "каналу, руководство пользователя, акты прав по приложению 1, гарантия.",
        "",
    ]
    OUTPUT.write_text("\n".join(document), encoding="utf-8")
    with CSV_OUTPUT.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    print("Source clauses:", len(rows), "Planning:", plan, "Actual:", done, "P0:", p0)
    print("Markdown bytes:", OUTPUT.stat().st_size, "CSV bytes:", CSV_OUTPUT.stat().st_size)

if __name__ == "__main__":
    main()
