#!/usr/bin/env python3
"""Build source-verified legacy museum pages from downloaded official HTML only.

No guessed titles, placeholder content, synthetic originals or OCR.
Pages not in the verified corpus remain unconverted pending actual source review.
"""
from __future__ import annotations
import json,hashlib,re
from pathlib import Path
from urllib.parse import urlsplit
from lxml import html as lx
from lxml import etree
from build_museum_legacy_page_aliases import build_map
ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'apps/web/src/data'
OUT=DATA/'official-original-legacy-sections.json'
SOURCES=(('official-page-snapshots.json','pages'),
 ('official-museum-menu-gaps.json','pages'),('official-science-sources.json','pages'),
 ('official-excursion-pages.json','pages'),('official-visitor-guidance.json','pages'),
 ('official-exhibition-indexes.json','indexes'),
 ('official-remaining-original-sections.json','pages'))
SOURCE_HOST='https://muzei-xleb.ru'

def build():
    canonical=build_map(); candidates={}
    for fname,key in SOURCES:
        doc=json.loads((DATA/fname).read_text(encoding='utf-8'))
        if doc.get('source')!=SOURCE_HOST:raise RuntimeError('Not real original museum source: '+fname)
        for source in doc[key]:
            url=source.get('source_url','')
            parsed=urlsplit(url);path=parsed.path.rstrip('/')
            if (parsed.scheme!='https' or parsed.netloc!='muzei-xleb.ru'
                or parsed.query or path not in canonical or not source.get('html')):continue
            kind=canonical[path]['why']
            if not (kind.startswith('menu:') or kind in ('original-news-list','original-exhibition-index','original-excursion-index','original-workshop-index','original-source-section')):
                continue
            body=source['html'];sha=source.get('html_sha256')
            if not isinstance(sha,str) or hashlib.sha256(body.encode()).hexdigest()!=sha:
                raise RuntimeError('Original source HTML signature failed '+url)
            if not 12<len(body)<2_000_000 or not source.get('title'):
                raise RuntimeError('Original source incomplete '+url)
            if path in candidates:
                old=candidates[path]
                if old['html_sha256']!=sha:raise RuntimeError('Original source conflict '+url)
                continue
            image_links=source.get('image_links',[])
            if path=='/novosty' and fname=='official-remaining-original-sections.json':
                # Literal ten original JPEG anchors in the saved museum news
                # index. Preserve as gallery, not empty anchors after sanitization.
                image_links=[{'url':link['href'],'alt':source['title']} for link in source['source_links']
                    if link['href'].startswith(SOURCE_HOST+'/sites/default/files/')
                    and re.search(r'\.(jpe?g|png|webp)$',urlsplit(link['href']).path,re.I)]
                if len(image_links)!=10:raise RuntimeError('Genuine current-news index gallery incomplete')
            if not image_links and 'image_sources' in source:
                image_links=[{'url':x['source_url'],'alt':x.get('alt','')} for x in source['image_sources']]
            candidates[path]={
                'path':path,'source_url':url,'title':source['title'],
                'html':body,'html_sha256':sha,
                'image_links':image_links,'source_record':fname,
                'kind':kind,
                'target_was':canonical[path]['target'],
            }
    # The 4 exhibition catalog paths are /vistavky/<slug>, all others root.
    if len(candidates)!=37:raise RuntimeError(f'Expected 37 genuine original museum section pages; found {len(candidates)}')
    if sum(p.startswith('/vistavky/') for p in candidates)!=4:
        raise RuntimeError('Incomplete four verified museum exhibition catalog originals')
    original={
        'source':SOURCE_HOST,'count':len(candidates),
        'sections':list(candidates.values()),
        'missing_originals':sorted(set(path for path,item in canonical.items() if
            (item['why'].startswith('menu:') or item['why'] in ('original-excursion-index','original-workshop-index','original-news-list','original-exhibition-index'))
            and path not in candidates)),
    }
    OUT.write_text(json.dumps(original,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('SOURCE_VERIFIED_OLD_MUSEUM_SECTIONS',len(candidates),'self-contained source pages',
        len(original['missing_originals']),'genuine unverified section origins',original['missing_originals'],flush=True)
    return original
if __name__=='__main__':build()
