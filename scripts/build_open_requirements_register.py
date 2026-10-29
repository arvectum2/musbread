#!/usr/bin/env python3
"""Deterministic read-only report of outstanding contract requirements."""
import argparse
import collections
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'docs/tz-audit/requirements.psv'
OUTPUT = ROOT / 'docs/tz-audit/OPEN_REQUIREMENTS_20261029.md'
FIELDS = ('ID', 'Пункт ТЗ', 'Атомарное обязательство', 'Фактически готово', 'Осталось выполнить', 'Нужно от заказчика', 'Приоритет')

def safe(value):
    return str(value or '—').replace('|', '\\|').replace('\n', ' ').replace('\r', ' ').strip()

def render(rows):
    counts = collections.Counter(r['Фактически готово'] for r in rows)
    lines = ['# Открытые требования ТЗ — реестр исполнения', '',
             'Срез матрицы на 29.10.2026. Создан автоматически из `requirements.psv`; не является актом приёмки.', '',
             f"Всего: {len(rows)}; готово: {counts['Да']}; частично: {counts['Частично']}; не начато: {counts['Нет']}.", '',
             'Статусы наследуются из первичной матрицы; генератор не повышает готовность без подтверждений.', '']
    for status, heading in [('Частично', 'Жёлтые — частично выполнено'), ('Нет', 'Красные — не начато / не подтверждено')]:
        subset = [r for r in rows if r['Фактически готово'] == status]
        lines += [f'## {heading} ({len(subset)})', '',
                  '| ID | Приоритет | Требование | Что осталось | Нужно от заказчика |',
                  '|---|---|---|---|---|']
        for r in subset:
            lines.append('| ' + ' | '.join(safe(r[k]) for k in ('ID', 'Приоритет', 'Атомарное обязательство', 'Осталось выполнить', 'Нужно от заказчика')) + ' |')
        lines.append('')
    return '\n'.join(lines)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true', help='fail if output differs')
    args = parser.parse_args()
    with SOURCE.open(encoding='utf-8-sig', newline='') as f:
        rows = list(csv.DictReader(f, delimiter='^'))
    if len(rows) != 325 or len({r['ID'] for r in rows}) != 325 or any(not all(r.get(k) for k in FIELDS) for r in rows):
        raise SystemExit('Invalid requirements matrix: expected 325 unique, complete rows')
    content = render(rows)
    if args.check:
        if not OUTPUT.exists() or OUTPUT.read_text(encoding='utf-8') != content:
            raise SystemExit('Open requirements report is stale; regenerate it')
        print('Open requirements report up to date')
    else:
        OUTPUT.write_text(content, encoding='utf-8')
        print(f'Wrote {OUTPUT.relative_to(ROOT)}')

if __name__ == '__main__':
    main()
