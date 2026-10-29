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

# Pages independently rendered at their original path are NOT redirects.
# A navigation fallback target can be absent under CMS-approved navigation,
# while the canonical source page is still present and must not be deleted.
NATIVE_REASONS=frozenset({
    'original-news-article','original-exhibition-detail',
    'original-news-node-exhibition','original-excursion-detail',
    'original-workshop-detail','original-exposition-room',
    'original-source-section','original-crosslink-page','original-deep-page',
})



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
    known_exhibition_targets={}
    for file in ('official-exhibition-details.json','official-exhibition-archive.json','official-exhibition-news-linked.json'):
        corpus=json.loads((DATA/file).read_text(encoding='utf-8'))
        if corpus['source']!=SOURCE:raise RuntimeError('Unverified museum exhibition source '+file)
        for item in corpus['exhibitions']:
            destination=f"/guide/{item['category_slug']}/#{item['slug']}"
            known_exhibition_targets[item['source_url']]=destination
            put(item['source_url'],destination,'original-exhibition-detail')
    # Each /node/N alias below was LITERALLY present in true source news,
    # resolved via the actual old Drupal server and checked against the
    # corresponding canonical museum exhibition path. Never invent mappings.
    verified_nodes_file=DATA/'official-node-linked-exhibitions.json'
    if verified_nodes_file.exists():
        linked=json.loads(verified_nodes_file.read_text(encoding='utf-8'))
        if linked.get('source')!=SOURCE or linked.get('node_count')!=61:
            raise RuntimeError('Incomplete historical museum Drupal node source record')
        for item in linked['exhibitions']:
            target=f"/guide/{item['category_slug']}/#{item['slug']}"
            if item['source_url'] in known_exhibition_targets:
                raise RuntimeError('Source exhibition record duplicates previously verified museum catalogue')
            known_exhibition_targets[item['source_url']]=target
            put(item['source_url'],target,'original-news-node-exhibition')
        for node in linked['verified_node_targets']:
            target=known_exhibition_targets.get(node['source_url'])
            if not target:
                raise RuntimeError('Original node has no verified separate museum exhibition destination')
            put(node['node_path'],urlsplit(node['source_url']).path+'/',
                'source-verified-drupal-node')
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
    # These top-level and exhibition-catalog paths have exact original HTML
    # separately verified against the actual museum source and export 200 pages.
    original_sections=DATA/'official-original-legacy-sections.json'
    if original_sections.exists():
        corpus=json.loads(original_sections.read_text(encoding='utf-8'))
        if corpus.get('source')!=SOURCE or corpus.get('count')!=37:
            raise RuntimeError('Incomplete original museum sections source corpus')
        for item in corpus['sections']:
            old= item['path']
            if old not in mapping or not mapping[old]['why'].startswith(('menu:','original-')):
                raise RuntimeError('Unlisted/unsafe original museum old section '+old)
            mapping[old]={'target':mapping[old]['target'],'why':'original-source-section'}
    # Secondary source audit found full genuine museum documents and video
    # pages linked from originals; preserve their actual canonical paths.
    more=DATA/'official-museum-crosslink-pages.json'
    if more.exists():
        extra=json.loads(more.read_text(encoding='utf-8'))
        if extra.get('source')!=SOURCE or extra.get('count')!=15 or len(extra.get('redirects',[]))!=10:
            raise RuntimeError('Verified museum source crosslink corpus incomplete')
        for page in extra['pages']:
            put(page['source_url'],'/guide/museum-media/' if page['path'].startswith('/video/') else '/guide/museum-documents/',
                'original-crosslink-page')
        for redirect in extra['redirects']:
            if redirect.get('original_server_redirect_proven') is not True:
                raise RuntimeError('Unproven original Drupal 301 proposed')
            put(redirect['original_node'],redirect['effective_path']+'/', 'source-verified-drupal-node')
    # Nested original museum links discovered after the 518-URL checkpoint.
    # Their old Drupal node targets have been independently followed over
    # direct Mac mini HTTP, retaining only genuine source effective paths.
    deep=DATA/'official-deep-museum-pages.json'
    if deep.exists():
        d=json.loads(deep.read_text(encoding='utf-8'))
        if d.get('source')!=SOURCE or len(d.get('pages',[]))!=d.get('count') or not isinstance(d.get('redirects'),list):
            raise RuntimeError('Unverified deeper museum source path mapping')
        for item in d['pages']:
            if item['source_url']!=SOURCE+item['path']:
                raise RuntimeError('Fabricated old museum canonical URL '+str(item['path']))
            put(item['source_url'],'/guide/exhibitions-past/' if item['path'].startswith('/vistavky/') else '/guide/museum-documents/',
                'original-deep-page')
        for item in d['redirects']:
            if item.get('original_server_redirect_proven') is not True:
                raise RuntimeError('No evidence for numeric old Drupal redirect')
            put(item['original_node'],item['effective_path']+'/', 'source-verified-drupal-node')
    return mapping


def build_aliases(write=True,strict=True):
    mapping=build_map()
    if not OUT.is_dir():raise RuntimeError('Next.js static output missing; build first')
    collisions=[];missing=[];written=[]
    rows=[]
    for source,meta in sorted(mapping.items()):
        target=meta['target'];uri=urlsplit(target)
        dest=OUT/(uri.path.lstrip('/'))/'index.html'
        native=meta['why'] in NATIVE_REASONS
        if not dest.is_file() and (not native or bool(uri.fragment)):
            missing.append((source,target));continue
        if uri.fragment:
            payload=dest.read_text(encoding='utf-8')
            if f'id="{uri.fragment}"' not in payload and f'id=\"{uri.fragment}\"' not in payload:
                missing.append((source,target+' (missing anchor)'));continue
        alias=OUT/(source.lstrip('/'))/'index.html'
        if native:
            # Native, independently generated Next.js route at the ORIGINAL
            # indexable museum URL. Never overwrite it with a meta-refresh.
            if not alias.is_file():
                missing.append((source,'missing independently rendered original 200 HTML'));continue
            original_html=alias.read_text(encoding='utf-8')
            required_canonical=SOURCE+source
            required_marker=('data-official-original-news=' if meta['why']=='original-news-article'
                             else 'data-original-museum-exhibition=' if meta['why'] in ('original-exhibition-detail','original-news-node-exhibition') or meta['why']=='original-deep-page' and source.startswith('/vistavky/')
                             else 'data-original-museum-room=' if meta['why']=='original-exposition-room'
                             else 'data-original-museum-section=' if meta['why'] in ('original-source-section','original-crosslink-page','original-deep-page')
                             else 'data-original-museum-program=')
            # Next.js trailingSlash=true may normalize absolute canonical
            # URLs when metadataBase is the SAME official source host.
            # The museum's original source paths in verified old HTML do not
            # have that trailing slash. Restore exactly one source-backed
            # <link rel=canonical> in the deployed static HTML instead of
            # silently rewriting all 467 URLs and losing canonical history.
            matched=re.search(r'<link rel="canonical" href="([^"]+)"',original_html)
            if not matched or matched.group(1) not in (required_canonical,required_canonical+'/'):
                raise RuntimeError('Unapproved canonical target in original source page '+source)
            if matched.group(1)==required_canonical+'/' and write:
                original_html=(original_html[:matched.start(1)]+required_canonical+
                    original_html[matched.end(1):])
                alias.write_text(original_html,encoding='utf-8')
            if (required_marker not in original_html
                or f'<link rel="canonical" href="{required_canonical}"' not in original_html
                or 'http-equiv="refresh"' in original_html.lower()
                or (alias.parent/'.musbread-legacy-alias').exists()):
                raise RuntimeError('Original museum source URL lacks standalone source-exact canonical HTML: '+source)
            rows.append({'legacy_path':source,'new_relative_url':target if dest.is_file() else source,'source_kind':meta['why'],
                         'mode':'native-source-URL-200; no redirect'})
            continue
        # The full static release intentionally strips private marker files.
        # A later read-only audit must nevertheless recognise its *exact*
        # generated fallback HTML without treating it as an unsafe collision.
        # Any unknown/mutated HTML at this original URL remains a hard error.
        origin_html=escape(source,quote=True)
        url=escape(target,quote=True)
        html=('<!doctype html><html lang="ru"><head><meta charset="utf-8">'
              '<meta name="viewport" content="width=device-width,initial-scale=1">'
              '<meta name="robots" content="noindex,follow">'
              '<meta http-equiv="refresh" content="0;url='+url+'">'
              '<title>Страница музея перенесена</title></head>'
              '<body><a tabindex="0" class="skip-link" href="#main">'
              'Перейти к основному содержимому</a>'
              '<main id="main"><h1>Страница музея перенесена</h1>'
              '<p>Оригинальная страница музея переехала: '
              '<a tabindex="0" title="Открыть материал музея" href="'+url+'">'
              'открыть материал нового сайта</a>.</p>'
              '<p>Исторический адрес: '+origin_html+'</p></main></body></html>')
        if (alias.resolve()==dest.resolve()
            or (alias.exists() and not (alias.parent/'.musbread-legacy-alias').exists()
                and alias.read_text(encoding='utf-8') != html+'\n')):
            collisions.append((source,target));continue
        rows.append({'legacy_path':source,'new_relative_url':target,'source_kind':meta['why'],'mode':'static-meta-refresh; HTTP 301 requires approved webserver config'})
        if write:
            alias.parent.mkdir(parents=True,exist_ok=True)
            # TZ-207: a non-Nginx fallback has landmarks, keyboard skip link
            # and a source-verified ordinary link, without changing HTTP 301.
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
