#!/usr/bin/env python3
"""Enumerate source-verified internal links in all migrated ORIGINAL museum bodies.
No SEO coverage claims for unseen pages and no invented redirects.
"""
from __future__ import annotations
import collections,csv,hashlib,json,re,sys
from pathlib import Path
from urllib.parse import urljoin,urlsplit
from lxml import html
ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'apps/web/src/data'
OUT=ROOT/'docs/seo/ORIGINAL_MUSEUM_CROSSLINK_GAPS_20261018.csv'
sys.path.insert(0,str(ROOT/'scripts'))
from build_museum_legacy_page_aliases import build_map
SOURCES=[('official-museum-news.json','articles'),('official-museum-news-archive.json','articles'),('official-exhibition-details.json','exhibitions'),('official-exhibition-archive.json','exhibitions'),('official-exhibition-news-linked.json','exhibitions'),('official-node-linked-exhibitions.json','exhibitions'),('official-excursion-programs.json','programs'),('official-workshop-pages.json','programs'),('official-exposition-rooms.json','rooms'),('official-original-legacy-sections.json','sections'),('official-museum-crosslink-pages.json','pages')]
def collect():
  original=[]
  for name,key in SOURCES:
    d=json.loads((SRC/name).read_text(encoding='utf-8'))
    for a in d[key]:
      if hashlib.sha256(a['html'].encode()).hexdigest()!=a['html_sha256']:
        raise RuntimeError('Museum source digest wrong '+a['source_url'])
      for el in html.fragment_fromstring(a['html'],create_parent='div').xpath('.//a[@href]'):
        href=el.get('href','')
        u=urlsplit(urljoin(a['source_url'],href))
        if u.hostname not in ('muzei-xleb.ru','www.muzei-xleb.ru') or not u.path or u.path=='/':continue
        original.append({'linked_path':u.path,'linked_query':u.query,
          'original_link':href,'original_referrer':a['source_url'],
          'original_anchor_text':' '.join(el.text_content().split())[:120]})
  paths=build_map()
  photos=json.loads((SRC/'official-museum-photo-assets.json').read_text())['photos']
  index_photos=json.loads((SRC/'official-news-index-photo-assets.json').read_text())['photos']
  photopath={urlsplit(x).path for x in photos}|{urlsplit(x).path for x in index_photos}
  documents=json.loads((ROOT/'docs/source-migration/OFFICIAL_ORIGINAL_DOCUMENTS_DEPLOYMENT_20261018.json').read_text())['files']
  docpath={x['legacy_path'] for x in documents}
  gaps=[];seen=set()
  for r in original:
    path=r['linked_path'];query=r['linked_query'];extension=Path(path).suffix.lower()
    if path in paths:known='old-original-or-verified-drupal-path'
    elif path in docpath:known='byte-verified-original-document'
    elif path in photopath:known='self-hosted-original-photo'
    elif path.startswith('/sites/default/files/') and extension in ('.jpg','.jpeg','.png','.webp'):
      known='UNCOVERED_ORIGINAL_MUSEUM_IMAGE'
    elif path.startswith('/sites/default/files/') and extension in ('.pdf','.docx'):
      known='UNCOVERED_ORIGINAL_MUSEUM_DOCUMENT'
    else:known='UNCOVERED_ORIGINAL_MUSEUM_PAGE'
    if known.startswith('UNCOVERED'):
      key=(path,r['original_referrer'])
      if key not in seen:gaps.append({**r,'gap_type':known});seen.add(key)
  OUT.parent.mkdir(parents=True,exist_ok=True)
  with OUT.open('w',encoding='utf-8-sig',newline='') as f:
    fieldnames=['linked_path','linked_query','original_link','original_referrer','original_anchor_text','gap_type']
    writer=csv.DictWriter(f,fieldnames=fieldnames,delimiter=';',lineterminator='\n')
    writer.writeheader();writer.writerows(sorted(gaps,key=lambda x:(x['gap_type'],x['linked_path'],x['original_referrer'])))
  summary={'source_links':len(original),'unique_path_targets':len({r['linked_path'] for r in original}),
    'uncovered_unique_paths':len({r['linked_path'] for r in gaps}),
    'uncovered_by_category':dict(collections.Counter(x['gap_type'] for x in gaps)),
    'queries':sorted({r['linked_query'] for r in original if r['linked_query']})}
  print('FULL_SOURCE_BACKED_MUSEUM_INTERNAL_CROSSLINK_AUDIT',summary,flush=True)
  return summary
if __name__=='__main__':collect()
