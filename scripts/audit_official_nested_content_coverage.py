#!/usr/bin/env python3
"""Source-only comparison of original museum internal editorial links against copied pages.

No network, private visitor data, invented articles, media or guessed URLs.
Outputs a candidate gap list, not a claim that original links are accessible.
"""
from __future__ import annotations
import csv,json
from collections import defaultdict, Counter
from pathlib import Path
from urllib.parse import urlparse
from lxml import html
ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'apps/web/src/data'
REPORT=ROOT/'docs/source-migration/NESTED_CATALOG_LINK_GAPS_20261018.md'
CSV=ROOT/'docs/source-migration/NESTED_CATALOG_LINK_GAPS_20261018.csv'
SOURCES={
 'official-page-snapshots.json':['pages'],
 'official-museum-menu-gaps.json':['pages'],
 'official-excursion-pages.json':['pages'],
 'official-excursion-programs.json':['programs'],
 'official-workshop-pages.json':['programs'],
 'official-exhibition-indexes.json':['indexes'],
 'official-exhibition-details.json':['exhibitions'],
 'official-exhibition-archive.json':['exhibitions'],
 'official-exhibition-news-linked.json':['exhibitions'],
 'official-museum-videos.json':['groups'],
 'official-exposition-rooms.json':['rooms'],
 'official-museum-news.json':['articles'],
 'official-museum-news-archive.json':['articles'],
 'official-science-sources.json':['pages'],
 'official-visitor-guidance.json':['pages'],
}
PREFIXES=('ekspozicii','ekskursii','master-klassy','vistavky','novosty','video',
          'nauka','nauchnaya','obrazovanie','dokumenty','posetitelyam')

def run():
    captured=set();articles=[];links=defaultdict(set);menu=set()
    for file,keys in SOURCES.items():
        data=json.loads((DATA/file).read_text(encoding='utf-8'))
        assert data['source']=='https://muzei-xleb.ru',file
        for key in keys:
            for item in data.get(key,[]):
                if not isinstance(item,dict):continue
                page=item.get('source_url')
                if page and urlparse(page).hostname=='muzei-xleb.ru':captured.add(urlparse(page).path.rstrip('/'))
                if item.get('html'):
                    node=html.fragment_fromstring(item['html'],create_parent='div')
                    for anchor in node.xpath('.//a[@href]'):
                        target=urlparse(anchor.get('href'))
                        if target.hostname!='muzei-xleb.ru' or not target.path.strip('/'):continue
                        path=target.path.rstrip('/')
                        if path.startswith('/sites/default/files/') or path.startswith('/system/files/'):
                            continue
                        links[path].add((page or file, ' '.join(anchor.text_content().split())[:85]))
                for key2 in ('linked_exhibitions',):
                    for x in item.get(key2,[]):
                        target=urlparse(x.get('source_url',''))
                        if target.hostname=='muzei-xleb.ru':
                            links[target.path.rstrip('/')].add((page or file,x.get('title','')[:85]))
    with (ROOT/'docs/source-migration/ORIGINAL_MENU_COVERAGE_20261018.csv').open(encoding='utf-8-sig',newline='') as f:
        for item in csv.DictReader(f,delimiter=';'):
            menu.add(item['path'].rstrip('/'))
    covered=captured|menu
    candidates=[]
    for path,refs in links.items():
        if path in covered:continue
        if not path.lstrip('/').startswith(PREFIXES):continue
        if path in ('/novosty','/video','/ekspozicii'):continue
        # Older archive news are a separate, deliberately incomplete task.
        if path.startswith('/novosty/'):
            continue
        source=sorted(refs)
        candidates.append({'path':path,'referring_count':len(refs),
            'first_referrer':source[0][0],'original_link_text':source[0][1],
            'audit_status':'not-in-current-captured-corpus; live verification required'})
    candidates.sort(key=lambda r:(r['path'].split('/')[1],r['path']))
    CSV.parent.mkdir(parents=True,exist_ok=True)
    with CSV.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(candidates[0]) if candidates else ['path','referring_count','first_referrer','original_link_text','audit_status'],delimiter=';',lineterminator='\n');w.writeheader();w.writerows(candidates)
    lines=['# Вложенные музейные каталоги: сверка реальных ссылок с уже перенесённым корпусом','','**Автоматическая сверка сохранённых подлинных HTML-страниц и 41 пункта меню, без новых запросов к сайту.** Не найденная в корпусе цель может быть служебной, устаревшей, редиректом или внешне связанной страницей. Нельзя считать список подтверждёнными недостающими статьями, пока оригинальный адрес не проверен напрямую.','','- Существующих в списках материалов URL: **'+str(len(captured))+'**.','- Оригинальных меню-ссылок: **'+str(len(menu))+'**.','- Найдено внутренних переходов на музейные страницы: **'+str(len(links))+'**.','- Отсутствуют в известных снимках/меню и требуют проверки: **'+str(len(candidates))+'** (архив новостей исключён, у него отдельная очередь).','','| Подлинный путь | Откуда найден | Ссылок |','|---|---|---:|']
    for row in candidates[:80]:
        lines.append(f"| [{row['path']}](https://muzei-xleb.ru{row['path']}) | {row['first_referrer']} | {row['referring_count']} |")
    lines+=['','Каждый будущий перенос начинается с HTTP-проверки оригинала, последующей сверки действительного музейного текста и сохранения SHA-256. Не создавать страницу/заменитель по имени ссылки без первоисточника.','', 'Полный машиночитаемый список: [CSV](NESTED_CATALOG_LINK_GAPS_20261018.csv).']
    REPORT.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print('NESTED_CATALOG_AUDIT',len(captured),'source pages,',len(links),'link targets,',len(candidates),'needs verified original')
    print('BY_PREFIX',dict(Counter(x['path'].split('/')[1] for x in candidates)))
    return candidates
if __name__=='__main__':run()
