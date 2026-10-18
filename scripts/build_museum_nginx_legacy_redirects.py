#!/usr/bin/env python3
"""Prepare *unapplied* real HTTP 301 museum-domain cutover rules for Nginx.

Unlike static HTML/JS navigation, this covers old external bookmarks and
embedded Drupal JPEG URLs. All mappings originate in verified museum pages or
original image bytes already embedded in the immutable static site. Generate
no absolute self-redirects; deploy only with an approved production host.
"""
from __future__ import annotations
import json,re
from pathlib import Path
from urllib.parse import urlsplit
from build_museum_legacy_page_aliases import build_map
ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'apps/web/src/data/official-museum-photo-assets.json'
OUTPUT=ROOT/'deploy/nginx/legacy_museum_redirects.map.conf'
SERVER=ROOT/'deploy/nginx/legacy_museum_redirects.server.conf'
ALLOWED=re.compile(r'^/[A-Za-z0-9._~%!$&\x27()*+,;=:@/-]+$')
NEW=re.compile(r'^/(?:[a-z0-9-]+/)*(?:[a-z0-9-]+|[a-f0-9]{64}\.webp)?(?:#[a-z0-9-]+)?$')

def render():
    routes={}
    kinds={}
    def register(source:str,target:str,kind:str):
        source=urlsplit(source).path.rstrip('/') or '/'
        if not ALLOWED.fullmatch(source):raise ValueError('Invalid source legacy path '+source)
        if not NEW.fullmatch(target):raise ValueError('Unverified/non-local museum new destination '+target)
        if source==urlsplit(target).path.rstrip('/'):
            raise ValueError('Self-referential museum redirect forbidden: '+source)
        old=routes.get(source)
        if old and old!=target:raise ValueError(f'Conflicting museum old URL {source}: {old} / {target}')
        routes[source]=target
        kinds[source]=kind
    old_pages=build_map()
    for source,item in old_pages.items():
        if item['why']=='original-news-article':
            # Native original date-based museum article is 200; new technical
            # /news/ copy gets a single 301 TO the historic human-readable URL.
            register(item['target'],source,'new_news_duplicate_to_original')
        elif item['why'] in ('original-exhibition-detail','original-news-node-exhibition','original-excursion-detail','original-workshop-detail','original-exposition-room','original-source-section','original-crosslink-page','original-deep-page'):
            # Native /vistavky/YYYY-MM-DD/... is a full source-verified 200
            # page; NEVER redirect it to a generic catalogue-card anchor.
            continue
        else:
            register(source,item['target'],'page')
    photo_assets=json.loads(DATA.read_text(encoding='utf-8'))
    if photo_assets.get('source')!='https://muzei-xleb.ru' or photo_assets.get('count')!=len(photo_assets.get('photos',{})):
        raise ValueError('Not a verified museum photo corpus')
    for canonical,asset in photo_assets['photos'].items():
        if not canonical.startswith('https://muzei-xleb.ru/sites/default/files/'):
            raise ValueError('Foreign museum original photo')
        local=asset['path']
        if not re.fullmatch(r'/media/museum-source/[a-f0-9]{64}\.webp',local):
            raise ValueError('Museum original bytes not covered by local WebP')
        register(canonical,local,'original_photo')
        register(asset['source_image_url'],local,'original_photo_thumbnail')
    # Ten actual FULL-SIZE news-index photographs are distinct from the CMS
    # gallery set; retain original links in the real source main news page.
    index_asset_file=ROOT/'apps/web/src/data/official-news-index-photo-assets.json'
    index_photos=json.loads(index_asset_file.read_text(encoding='utf-8'))
    if index_photos.get('source')!='https://muzei-xleb.ru' or index_photos.get('count')!=10:
        raise RuntimeError('Extra news image originals not downloaded/verified')
    for original,entry in index_photos['photos'].items():
        if not original.startswith('https://muzei-xleb.ru/sites/default/files/novosty/'):
            raise ValueError('Unverified original museum image in news-index gallery')
        target=entry['path']
        if not re.fullmatch(r'/media/museum-source/[a-f0-9]{64}\.webp',target):
            raise ValueError('News museum original image not self-hosted')
        register(original,target,'original_news_index_photo')
    # Historical /novosti (not /novosty) contains 37 authentic linked JPEGs.
    # Each literal source path is backed by locally saved raw source SHA and
    # an exported WebP; avoid dependence on retiring Drupal after DNS cutover.
    deep_file=ROOT/'apps/web/src/data/official-deep-news-image-assets.json'
    deep=json.loads(deep_file.read_text(encoding='utf-8'))
    if deep.get('source')!='https://muzei-xleb.ru' or deep.get('count')!=len(deep.get('photos',{})):
        raise RuntimeError('Deep museum photo source corpus malformed')
    if deep['count']+len(deep.get('unavailable',[]))!=37:
        raise RuntimeError('Not all 37 source-linked historical museum JPEGs classified')
    for original,asset in deep['photos'].items():
        if not original.startswith('https://muzei-xleb.ru/sites/default/files/page/'):
            raise RuntimeError('Non-source old JPEG supplied as museum photo')
        local=asset['path']
        if not re.fullmatch(r'/media/museum-source/[a-f0-9]{64}\.webp',local):
            raise RuntimeError('Museum historical original not exported as independent local WebP')
        stored=ROOT/'apps/web/public'/local.lstrip('/')
        if not stored.is_file():raise RuntimeError('Exported museum old source photo missing '+local)
        register(original,local,'deep_original_museum_photo')
    # Four original exhibition gallery JPEG source links discovered in a real
    # 2019 article. Every photo was downloaded and verified against archived
    # museum source HTML and a local unmodified source JPG SHA-256.
    exhibit_file=ROOT/'apps/web/src/data/official-historical-exhibition-image-assets.json'
    exhibition=json.loads(exhibit_file.read_text(encoding='utf-8'))
    if exhibition.get('source')!='https://muzei-xleb.ru' or exhibition.get('count',-1)+len(exhibition.get('unavailable',[]))!=4:
        raise RuntimeError('Museum original 2019 exhibition image source incomplete')
    for original,asset in exhibition['photos'].items():
        if not original.startswith('https://muzei-xleb.ru/sites/default/files/vistavky/'):
            raise RuntimeError('Unverified source museum exhibition image URL')
        local=asset['path']
        if not re.fullmatch(r'/media/museum-source/[a-f0-9]{64}\.webp',local):
            raise RuntimeError('No local museum exhibit WebP target')
        stored=ROOT/'apps/web/public'/local.lstrip('/')
        if not stored.is_file():raise RuntimeError('Original exhibition image not stored as standalone file')
        register(original,local,'original_2019_exhibition_photo')
    output=['# GENERATED FROM source-verified museum HTML and local static WebP assets.',
            '# Include ONLY from the nginx http{} context, not server{}.',
            '# Redirects work only after you configure this as the museum domain itself.',
            '# Nginx normalized $uri ignores the old Drupal ?itok=... query parameter.',
            'map $uri $musbread_legacy_target {','    default "";']
    for source,target in sorted(routes.items()):
        output.append(f'    {source} \"{target}\";')
    output.append('}')
    OUTPUT.write_text('\n'.join(output)+'\n',encoding='utf-8')
    SERVER.write_text('# Include from the nginx server{} block that serves muzei-xleb.ru.\n'
      '# Nginx "if" with return ONLY is safe here; no rewriting to the same old domain.\n'
      'if ($musbread_legacy_target != "") {\n'
      '    return 301 $musbread_legacy_target;\n'
      '}\n',encoding='utf-8')
    counts={'total':len(routes),'page':sum(v in ('page','new_news_duplicate_to_original') for v in kinds.values()),
            'image':sum(v not in ('page','new_news_duplicate_to_original') for v in kinds.values()),
            'photo_original':photo_assets['count'],'news_index_original_photos':index_photos['count'],'deep_original_photos':deep['count'],'historical_exhibition_photos':exhibition['count']}
    if counts['page']!=sum(v['why'] not in ('original-exhibition-detail','original-news-node-exhibition','original-excursion-detail','original-workshop-detail','original-exposition-room','original-source-section','original-crosslink-page','original-deep-page')
                           for v in old_pages.values()) or counts['image']<photo_assets['count']:
        raise RuntimeError('Dropped museum original photo or page redirects')
    print('MUSEUM_PRODUCTION_HTTP301_CONFIG_PREPARED',counts,'not deployed',flush=True)
    return counts
if __name__=='__main__':render()
