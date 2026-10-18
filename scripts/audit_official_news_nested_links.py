#!/usr/bin/env python3
"""Audit REAL source-article embedded museum links; do not invent targets.

Historical Drupal /node/<id> pointers may not exist on the future server.
This inventory is content migration (which real museum pages are referred to),
not an assertion about existing SEO ranks or search console access.
"""
from __future__ import annotations
import collections,csv,json,re
from lxml import html
from pathlib import Path
from urllib.parse import urlsplit
ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'apps/web/src/data'
CSV=ROOT/'docs/source-migration/NEWS_ARCHIVE_NESTED_ORIGINAL_LINKS_20261018.csv'

def audit():
    sources=[]
    for name in ('official-museum-news.json','official-museum-news-archive.json'):
        d=json.loads((DATA/name).read_text(encoding='utf-8'))
        if d['source']!='https://muzei-xleb.ru':raise RuntimeError('Original museum news corpus changed')
        sources+=d['articles']
    known=set()
    for name,key in [('official-exhibition-details.json','exhibitions'),('official-exhibition-archive.json','exhibitions'),('official-exhibition-news-linked.json','exhibitions'),('official-excursion-programs.json','programs'),('official-workshop-pages.json','programs'),('official-page-snapshots.json','pages'),('official-museum-menu-gaps.json','pages')]:
        d=json.loads((DATA/name).read_text(encoding='utf-8'))
        for a in d[key]:known.add(a.get('source_url'))
    known.update(a['source_url'] for a in sources)
    collected={}
    for article in sources:
        for tag in html.fragment_fromstring(article['html'],create_parent='div').xpath('.//a[@href]'):
            href=tag.get('href','')
            u=urlsplit(href)
            if u.hostname!='muzei-xleb.ru' or u.scheme not in ('http','https') or not u.path.startswith('/'):continue
            if u.path.startswith('/sites/default/files/'):continue
            canonical='https://muzei-xleb.ru'+u.path
            kind=('legacy-node' if re.fullmatch(r'/node/\d+',u.path) else
                  'source-page-known' if canonical in known else
                  'museum-site-original-other')
            key=(u.path,article['source_url'])
            collected[key]={'original_link_path':u.path,'original_link_url':href,
               'source_article':article['source_url'],
               'source_anchor_text':' '.join(tag.text_content().split())[:180],
               'content_check':kind,'verified_target_url':canonical if kind=='source-page-known' else ''}
    results=sorted(collected.values(),key=lambda x:(x['original_link_path'],x['source_article']))
    with CSV.open('w',encoding='utf-8-sig',newline='') as f:
        fieldnames=['original_link_path','original_link_url','source_article','source_anchor_text','content_check','verified_target_url']
        w=csv.DictWriter(f,fieldnames=fieldnames,delimiter=';',lineterminator='\n')
        w.writeheader();w.writerows(results)
    types=collections.Counter(x['content_check'] for x in results)
    distinct={x['original_link_path'] for x in results}
    nodes={x['original_link_path'] for x in results if x['content_check']=='legacy-node'}
    print('VERIFIED_NEWS_NESTED_LINKS',len(results),'link references',len(distinct),'unique paths',len(nodes),'legacy Drupal numeric nodes',dict(types),flush=True)
    return {'rows':len(results),'distinct_paths':len(distinct),'legacy_nodes':len(nodes),'kinds':dict(types)}
if __name__=='__main__':audit()
