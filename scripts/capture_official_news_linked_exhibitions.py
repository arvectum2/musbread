#!/usr/bin/env python3
"""Four REAL original exhibition pages found via links in original museum news.

Do not change the 24-item signed exhibition catalogues: these two pages
are independently sourced from authentic archived news HTML links.
Uses only already downloaded museum originals on ArvectumSSD.
"""
from __future__ import annotations
from pathlib import Path
from datetime import datetime,timezone
from hashlib import sha256
from lxml import html
import json
from capture_official_museum_pages import HOST,parse
ROOT=Path(__file__).resolve().parents[1]
ARCHIVE=ROOT/'.local_archive/official-site-originals'
OUT=ROOT/'apps/web/src/data/official-exhibition-news-linked.json'
SOURCES=(
  ('/vistavky/2025-09-08/dom-na-treh-ulicah','museum-news-2025-09-22-vystavka-dom-na-tryoh-ulicah'),
  ('/vistavky/2025-09-22/v-serdce-azii','museum-news-2025-09-22-vystavka-v-serdce-azii'),
  ('/vistavky/2019-02-13/seriya-mini-vystavok-korotkoy-strokoy','museum-news-2021-04-09-vystavka-ko-dnyu-kosmonavtiki'),
  ('/vistavky/2021-04-13/v-gostyah-u-skazki-13-aprelya-29-maya-2021-g','museum-news-2021-04-13-vystavka-v-gostyah-u-skazki'),
)

def main():
    news=json.loads((ROOT/'apps/web/src/data/official-museum-news-archive.json').read_text())
    if news.get('source')!=HOST or news.get('count',0)<80:
        raise RuntimeError('Source museum news archive not complete')
    by_slug={n['slug']:n for n in news['articles']}
    entries=[]
    for path,news_slug in SOURCES:
        n=by_slug.get(news_slug)
        if n is None or sha256(n['html'].encode()).hexdigest()!=n['html_sha256']:
            raise RuntimeError('Linked museum news source is not verified')
        links=[a.get('href','') for a in html.fragment_fromstring(n['html'],create_parent='div').xpath('.//a[@href]')]
        if sum(href in (HOST+path,'http://muzei-xleb.ru'+path) for href in links)!=1:
            raise RuntimeError('Original exhibition URL not literally present in actual museum news')
        original=ARCHIVE/(path.rsplit('/',1)[-1]+'-20251018-old-exhibition.html')
        if not original.is_file():
            original=ROOT/'.local_archive/news-linked-exhibition-originals'/(path.rsplit('/',1)[-1]+'.html')
        raw=original.read_text(encoding='utf-8')
        detail=parse(raw,path,datetime.now(timezone.utc).isoformat(timespec='seconds'),min_text_length=8)
        if detail['source_url']!=HOST+path or detail['text_length']<100:
            raise RuntimeError('Original museum exhibition detail has no real content')
        excerpt=' '.join(html.fragment_fromstring(detail['html'],create_parent='div').text_content().split())
        detail.update({'slug':'museum-exhibit-'+path.removeprefix('/vistavky/').replace('/','-'),
                'category_slug':'exhibitions-past','intro':excerpt[:245],
                'linked_news_slug':news_slug,'linked_news_url':n['source_url'],
                'linked_news_html_sha256':n['html_sha256'],
                'photos_rights_confirmed':False,'source_page_sha256':sha256(raw.encode()).hexdigest()})
        entries.append(detail)
        print('VERIFIED_NEWS_LINKED_EXHIBITION',detail['title'],'SOURCE',detail['source_url'],'TEXT',detail['text_length'],flush=True)
    OUT.write_text(json.dumps({'source':HOST,'count':4,'exhibitions':entries},ensure_ascii=False,indent=2)+'\n')
if __name__=='__main__':main()
