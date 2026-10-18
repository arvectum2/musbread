#!/usr/bin/env python3
"""Museum DNS cutover aliases for REAL source-backed legacy editorial URLs.

No untrusted redirects, no redirect to the same domain, no guessed content.
Works with Next.js output:'export', where next.config redirects() cannot work.
Writes tiny relative meta-refresh HTML entrypoints under out/ after build.
Requires every destination HTML and deep-link anchor to exist in static export.
This is a browser-compatible fallback, NOT an HTTP 301 (add server rules later).
"""
from __future__ import annotations
import csv,json,re,sys
from html import escape
from pathlib import Path
from urllib.parse import urlsplit
ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'apps/web/src/data'
OUT=ROOT/'apps/web/out'
DOC=ROOT/'docs/source-migration/LEGACY_MUSEUM_PAGE_ALIASES_20261018.csv'
SOURCE='https://muzei-xleb.ru'
VALID_PATH=re.compile(r'^/(?:[a-z0-9-]+/)*$')
VALID_SLUG=re.compile(r'^[a-z0-9]+(?:-[a-z0-9]+)*$')
VALID_SOURCE=re.compile(r'^/(?:[a-z0-9-]+/)*[a-z0-9-]+/?$')
MENU_RE=re.compile(r'legacy\("([a-z0-9-]+)",\s*"[^"]+",\s*"(/[^"?#]+)"\)')


def build_map():
    mapping={}
    def put(source,target,why):
        uri=urlsplit(source)
        path=uri.path.rstrip('/') or '/'
        if source.startswith('http://') or source.startswith('https://'):
            if uri.scheme!='https' or uri.netloc!='muzei-xleb.ru':
                raise RuntimeError('Only original museum domain supported '+source)
        elif not source.startswith('/'):
            raise RuntimeError('Invalid source URL '+source)
        if not (path=='/' or VALID_SOURCE.fullmatch(path)):
            raise RuntimeError('Unsafe original museum page URL '+path)
        u=urlsplit(target)
        if not target.startswith('/') or u.scheme or u.netloc or not VALID_PATH.fullmatch(u.path):
            raise RuntimeError('Unsafe new museum static destination '+target)
        if u.fragment and not VALID_SLUG.fullmatch(u.fragment):
            raise RuntimeError('Unsafe deep-link anchor '+target)
        if path==u.path.rstrip('/') or path=='/' and u.path=='/':
            if path!='/':raise RuntimeError('Redirect would loop '+path)
            return
        if path in mapping:
            existing=mapping[path]
            if existing['target']!=target:
                # E.g. the legacy Pushkin-card URL occurs twice in the
                # museum's menu; first official menu occurrence is canonical.
                if why.startswith('menu') and existing['why'].startswith('menu'):
                    return
                raise RuntimeError(f'Conflicting museum old URL {path}: {existing}, {target}')
            return
        mapping[path]={'target':target,'why':why}
    # Main menu source identities include genuine museum policy pages.
    menu=(DATA/'museum-reference.ts').read_text(encoding='utf-8')
    for slug,path in MENU_RE.findall(menu):
        put(path,f'/guide/{slug}/','menu:'+slug)
    put('/novosty','/news/','original-news-list')
    put('/vistavky','/guide/exhibitions-guide/','original-exhibition-index')
    put('/ekskursii','/guide/excursions-guide/','original-excursion-index')
    put('/master-klassy','/guide/children-workshops/','original-workshop-index')
    put('/video','/guide/museum-media/','original-museum-media')
    # Actual articles from the primary news page + archived historical indexes.
    for file in ('official-museum-news.json','official-museum-news-archive.json'):
        corpus=json.loads((DATA/file).read_text(encoding='utf-8'))
        if corpus['source']!=SOURCE:raise RuntimeError('Unverified museum news source '+file)
        for article in corpus['articles']:
            put(article['source_url'],f"/news/{article['slug']}/",'original-news-article')
    for file in ('official-exhibition-details.json','official-exhibition-archive.json','official-exhibition-news-linked.json'):
        corpus=json.loads((DATA/file).read_text(encoding='utf-8'))
        if corpus['source']!=SOURCE:raise RuntimeError('Unverified museum exhibition source '+file)
        for item in corpus['exhibitions']:
            put(item['source_url'],f"/guide/{item['category_slug']}/#{item['slug']}",'original-exhibition-detail')
    corpus=json.loads((DATA/'official-excursion-programs.json').read_text(encoding='utf-8'))
    if corpus['source']!=SOURCE:raise RuntimeError('Unverified original museum excursion programs')
    for item in corpus['programs']:
        put(item['source_url'],f"/guide/{item['category_slug']}/#{item['slug']}",'original-excursion-detail')
    corpus=json.loads((DATA/'official-workshop-pages.json').read_text(encoding='utf-8'))
    if corpus['source']!=SOURCE:raise RuntimeError('Unverified original museum workshops')
    for item in corpus['programs']:
        put(item['source_url'],f"/guide/children-workshops/#{item['slug']}",'original-workshop-detail')
    corpus=json.loads((DATA/'official-exposition-rooms.json').read_text(encoding='utf-8'))
    if corpus['source']!=SOURCE:raise RuntimeError('Unverified museum exhibition rooms')
    for item in corpus['rooms']:
        put(item['source_url'],f"/guide/museum-exposition/#{item['slug']}",'original-exposition-room')
    for file in ('official-exhibition-indexes.json','official-excursion-pages.json'):
        corpus=json.loads((DATA/file).read_text(encoding='utf-8'))
        if corpus['source']!=SOURCE:raise RuntimeError('Unverified exhibition/excursion index')
        items=corpus.get('indexes',corpus.get('pages',[]))
        for item in items:
            slug=item['slug'] if 'slug' in item else item.get('cms_slug','')
            if slug in ('exhibitions-current','exhibitions-past','exhibitions-virtual',
                    'exhibitions-traveling','excursion-overview','excursion-interactive',
                    'excursion-thematic','excursion-theatrical'):
                put(item['source_url'],f'/guide/{slug}/','original-editorial-catalogue')
    return mapping


def build_aliases(write=True,strict=True):
    mapping=build_map()
    if not OUT.is_dir():raise RuntimeError('Next.js static output missing; build first')
    collisions=[];missing=[];written=[]
    rows=[]
    for source,meta in sorted(mapping.items()):
        target=meta['target'];uri=urlsplit(target)
        dest=OUT/(uri.path.lstrip('/'))/'index.html'
        if not dest.is_file():
            missing.append((source,target));continue
        if uri.fragment:
            payload=dest.read_text(encoding='utf-8')
            if f'id="{uri.fragment}"' not in payload and f'id=\"{uri.fragment}\"' not in payload:
                missing.append((source,target+' (missing anchor)'));continue
        alias=OUT/(source.lstrip('/'))/'index.html'
        if alias.resolve()==dest.resolve() or alias.exists() and not (alias.parent/'.musbread-legacy-alias').exists():
            collisions.append((source,target));continue
        rows.append({'legacy_path':source,'new_relative_url':target,'source_kind':meta['why'],'mode':'static-meta-refresh; HTTP 301 requires approved webserver config'})
        if write:
            alias.parent.mkdir(parents=True,exist_ok=True)
            origin_html=escape(source,quote=True)
            url=escape(target,quote=True)
            html=('<!doctype html><html lang="ru"><head><meta charset="utf-8">'
                  '<meta name="robots" content="noindex,follow">'
                  '<meta http-equiv="refresh" content="0;url='+url+'">'
                  '<title>Страница музея перенесена</title></head>'
                  '<body><p>Оригинальная страница музея переехала: '
                  '<a href="'+url+'">открыть материал нового сайта</a>.</p>'
                  '<p>Исторический адрес: '+origin_html+'</p></body></html>')
            alias.write_text(html+'\n',encoding='utf-8')
            (alias.parent/'.musbread-legacy-alias').write_text(target+'\n')
            written.append(str(alias))
    if strict and missing:
        raise RuntimeError('Unknown/missing destination for original museum paths: '+str(missing[:25]))
    if strict and collisions:
        raise RuntimeError('Legacy alias conflicts with real new site page: '+str(collisions[:25]))
    if write:
        DOC.parent.mkdir(parents=True,exist_ok=True)
        with DOC.open('w',newline='',encoding='utf-8-sig') as f:
            writer=csv.DictWriter(f,fieldnames=list(rows[0]),delimiter=';',lineterminator='\n')
            writer.writeheader();writer.writerows(rows)
    print('MUSEUM_LEGACY_ALIASES',len(rows),'verified old paths',len(missing),'missing targets',len(collisions),'collisions',len(written),'generated',flush=True)
    if missing:print('MISSING_SAMPLES',missing[:14],flush=True)
    if collisions:print('CONFLICT_SAMPLES',collisions[:14],flush=True)
    return {'rows':rows,'missing':missing,'collisions':collisions}
if __name__=='__main__':
    import argparse
    ap=argparse.ArgumentParser()
    ap.add_argument('--dry-run',action='store_true')
    ap.add_argument('--allow-missing',action='store_true')
    args=ap.parse_args()
    build_aliases(write=not args.dry_run,strict=not args.allow_missing)
