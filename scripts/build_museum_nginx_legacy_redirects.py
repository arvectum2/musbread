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
NEW=re.compile(r'^/(?:[a-z0-9-]+/)*(?:[a-f0-9]{64}\.webp)?(?:#[a-z0-9-]+)?$')

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
    for source,item in old_pages.items():register(source,item['target'],'page')
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
    counts={'total':len(routes),'page':sum(v=='page' for v in kinds.values()),
            'image':sum(v!='page' for v in kinds.values()),
            'photo_original':photo_assets['count']}
    if counts['page']!=len(old_pages) or counts['image']<photo_assets['count']:
        raise RuntimeError('Dropped museum original photo or page redirects')
    print('MUSEUM_PRODUCTION_HTTP301_CONFIG_PREPARED',counts,'not deployed',flush=True)
    return counts
if __name__=='__main__':render()
