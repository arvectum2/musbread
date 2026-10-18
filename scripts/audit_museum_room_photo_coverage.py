#!/usr/bin/env python3
"""Precisely compare actual room/history museum snapshots to archived photos.

Reports all 11 halls and historical building; metadata only. No previews or
original photos distributed. Does NOT imply that rights are approved.
"""
from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / 'apps/web/src/data'
MANIFEST = ROOT / '.local_archive/museum-official-photos/manifest.json'
OUT = ROOT / 'docs/source-migration/EXPOSITION_GALLERY_COVERAGE_20261018.csv'
SUMMARY = ROOT / 'docs/source-migration/EXPOSITION_GALLERY_COVERAGE_20261018.md'


def run() -> list[dict]:
    rooms = json.loads((SOURCES / 'official-exposition-rooms.json').read_text(encoding='utf-8'))
    pages = json.loads((SOURCES / 'official-page-snapshots.json').read_text(encoding='utf-8'))
    manifest = json.loads(MANIFEST.read_text(encoding='utf-8'))
    if (rooms.get('source') != 'https://muzei-xleb.ru'
        or pages.get('source') != 'https://muzei-xleb.ru'
        or manifest.get('source') != 'https://muzei-xleb.ru'):
        raise RuntimeError('Museum original source mismatch')
    copies = defaultdict(set)
    for row in manifest['files']:
        if row['cms_slug'] in copies and row.get('source_image_index',0) in copies[row['cms_slug']]:
            raise RuntimeError('Duplicate image index claimed')
        copies[row['cms_slug']].add(row.get('source_image_index',0))
    expected = {}
    for room in rooms['rooms']:
        expected[room['slug']] = {
            'title': room['title'],
            'source_url': room['source_url'],
            'items': room['image_sources'],
        }
    building = [p for p in pages['pages'] if p['path'] == '/istoriya-zdaniya']
    if len(building) != 1 or len(expected) != 11:
        raise RuntimeError('11 halls and historical source must be genuine')
    expected['building-history'] = {
        'title': building[0]['title'],
        'source_url': building[0]['source_url'],
        'items': building[0]['image_links'],
    }
    result = []
    for slug, source in expected.items():
        original_count = len(source['items'])
        stored_indices = copies.get(slug, set())
        if not stored_indices <= set(range(original_count)):
            raise RuntimeError('Archived image index nonexistent in original source: ' + slug)
        result.append({
            'cms_slug': slug,
            'original_page_title': source['title'],
            'original_page_url': source['source_url'],
            'total_real_original_images': original_count,
            'archived_original_images': len(stored_indices),
            'still_to_copy': original_count-len(stored_indices),
            'next_original_image_index': next(
                (i for i in range(original_count) if i not in stored_indices), ''),
            'rights_status': 'private-not-verified',
        })
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(result[0]), delimiter=';', lineterminator='\n')
        w.writeheader()
        w.writerows(result)
    total = sum(r['total_real_original_images'] for r in result)
    saved = sum(r['archived_original_images'] for r in result)
    lines = [
        '# Фотографии 11 залов экспозиции и истории здания: пофайловая сверка',
        '',
        'Источник — только реально опубликованные изображения действующего'
        ' muzei-xleb.ru, сохранённые в снимках музейных страниц.',
        '',
        f'**Всего в этих 12 источниках: {total} фотографий;'
        f' сохранено без замены: {saved}; ещё не перенесено: {total-saved}.**',
        '',
        '| Зал / история | Сохранено | Исходно | Осталось |',
        '|---|---:|---:|---:|',
    ]
    for row in result:
        title = row['original_page_title'].replace('|', r'\|')
        lines.append(
            f"| {title} | {row['archived_original_images']} |"
            f" {row['total_real_original_images']} | {row['still_to_copy']} |"
        )
    lines += [
        '',
        'Подробные индексы оригиналов и официальные ссылки:'
        ' [EXPOSITION_GALLERY_COVERAGE_20261018.csv]'
        '(EXPOSITION_GALLERY_COVERAGE_20261018.csv).',
        '',
        'Изображения хранятся в закрытой CMS до проверки прав,'
        ' а нетронутые исходные JPEG/PNG/WebP — на ArvectumSSD.',
        'Никаких стоковых или сгенерированных замен.',
    ]
    SUMMARY.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print('GALLERY COVERAGE',len(result),'genuine pages',saved,'/',total,'photographs, remaining',total-saved)
    return result


if __name__ == '__main__':
    run()
