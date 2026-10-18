#!/usr/bin/env python3
"""Import only authentic additional museum pages discovered via original links.

Old /node IDs are proven literal links and HTTP-resolve to a stable official
human URL. Preserve actual server response HTML byte digest, never invent body.
"""
from __future__ import annotations
import json,hashlib,re
from pathlib import Path
from urllib.parse import urlsplit
from lxml import html,etree
ROOT=Path(__file__).resolve().parents[1]
PRIVATE=ROOT/'.local_archive/museum-crosslink-original-pages'
OUT=ROOT/'apps/web/src/data/official-museum-crosslink-pages.json'
HOST='https://muzei-xleb.ru'

def run():
    manifest=json.loads((PRIVATE/'manifest.json').read_text(encoding='utf-8'))
    if manifest.get('source')!=HOST or manifest.get('count')!=18:
        raise RuntimeError('Original additional museum source HTTP check incomplete')
    verified=[];redirects=[];unavailable=[];seen={}
    for record in manifest['pages']:
        path=record['path'];target=urlsplit(record['effective_url'])
        if target.scheme!='https' or target.netloc!='muzei-xleb.ru':
            raise RuntimeError('Original museum redirect departed from source '+path)
        if record['status']!=200:
            unavailable.append({'path':path,'status':record['status'],'effective_url':record['effective_url']})
            continue
        name=path.lstrip('/').replace('/','__')+'.html'
        raw=(PRIVATE/name).read_bytes()
        if hashlib.sha256(raw).hexdigest()!=record['source_html_sha256']:
            raise RuntimeError('Original museum source bytes altered '+path)
        tree=html.fromstring(raw)
        titles=tree.xpath('//h1')
        if len(titles)!=1:raise RuntimeError('Original H1 ambiguous '+path)
        title=' '.join(titles[0].text_content().split())
        if title!=record['h1']:raise RuntimeError('Original museum H1 not verified '+path)
        main=tree.xpath('//*[contains(concat(" ",normalize-space(@class)," ")," region-content ")]')
        if len(main)!=1:raise RuntimeError('Original museum main content absent '+path)
        body=''.join(etree.tostring(x,encoding='unicode',method='html') for x in main[0] if x.tag not in ('script','style'))
        if len(body)<20:raise RuntimeError('Original museum source empty '+path)
        effective=target.path.rstrip('/')
        if not re.fullmatch(r'/(?:[a-z0-9-]+/)*[a-z0-9-]+',effective):
            raise RuntimeError('Unsafe original effective museum public address '+effective)
        if path.startswith('/node/'):
            if effective==path:raise RuntimeError('Assumed old node redirect without actually resolving '+path)
            redirects.append({'original_node':path,'effective_path':effective,'http_status':200,
                              'original_server_redirect_proven':True})
        if effective in seen:
            if seen[effective]['html_sha256']!=hashlib.sha256(body.encode()).hexdigest():
                raise RuntimeError('Two original museum pages have conflicting canonical body '+effective)
            continue
        seen[effective]={'source_url':HOST+effective,'path':effective,'title':title,
            'html':body,'html_sha256':hashlib.sha256(body.encode()).hexdigest(),
            'source_html_sha256':record['source_html_sha256'],
            'original_entry_path':path,'image_links':[],
            'source_page_captured_at':'2026-10-18'}
        verified.append((path,effective,title,len(body)))
    # The existing exact source-backed /pushkinskaya-karta is already a real
    # 200 page; never overwrite it using a second (formerly /node/298) copy.
    existing=json.loads((ROOT/'apps/web/src/data/official-original-legacy-sections.json').read_text(encoding='utf-8'))
    existing_paths={a['path'] for a in existing['sections']}
    new=[a for a in seen.values() if a['path'] not in existing_paths]
    if len(new)!=15 or len(redirects)!=10 or len(unavailable)!=2:
        raise RuntimeError('Museum original linked-page verification cardinality changed '+str((len(new),len(redirects),len(unavailable))))
    doc={'source':HOST,'count':len(new),'pages':new,'redirects':redirects,'unavailable':unavailable}
    OUT.write_text(json.dumps(doc,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('EXTRA_AUTHENTIC_MUSEUM_PAGES',len(new),'FULL_200',len(redirects),'verified original numeric nodes',len(unavailable),'OLD_403',flush=True)
    for a in new:print('MIGRATED_EXTRA_ORIGINAL',a['path'],a['title'],len(a['html']),flush=True)
    return doc
if __name__=='__main__':run()
