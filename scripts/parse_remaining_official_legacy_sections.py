#!/usr/bin/env python3
"""Copy exact original museum region HTML from six directly verified pages.

No invented text or replacement dummy content. Preserve original source H1,
links, fragment SHA and page SHA. The old museum has some menu-only pages.
"""
from __future__ import annotations
import hashlib,json,re
from pathlib import Path
from lxml import html,etree
ROOT=Path(__file__).resolve().parents[1]
FROM=ROOT/'.local_archive/remaining-museum-original-section-html'
OUT=ROOT/'apps/web/src/data/official-remaining-original-sections.json'
SOURCE='https://muzei-xleb.ru'
PAGES=['informaciya-dlya-dariteley','master-klassy','novosty','posetitelyam','video','vistavky']

def parse():
    m=json.loads((FROM/'verification.json').read_text())
    if m['source']!=SOURCE or m['count']!=6:raise RuntimeError('Not original museum source-verification manifest')
    records={x['path']:x for x in m['pages']}
    copied=[]
    for slug in PAGES:
        path='/'+slug;record=records.get(path)
        p=FROM/(slug+'.html')
        if not record or record['status']!=200 or not p.is_file():raise RuntimeError('Old original index not downloaded '+path)
        raw=p.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=record['sha256']:
            raise RuntimeError('Original museum HTML bytes SHA mismatch '+path)
        page=html.fromstring(raw)
        titles=page.xpath('//h1')
        if len(titles)!=1:raise RuntimeError('Museum original page missing unique H1 '+path)
        title=' '.join(titles[0].text_content().split())
        if [title]!=record['titles']:raise RuntimeError('Old museum page H1 changed '+path)
        blocks=page.xpath('//*[contains(concat(" ",normalize-space(@class)," ")," region-content ")]')
        if len(blocks)!=1:raise RuntimeError('Museum original main content region missing '+path)
        region=blocks[0]
        # Preserve only the real primary region from the archived bytes;
        # Next.js RichText applies allowedTag sanitization on rendering.
        content=''.join(etree.tostring(child,encoding='unicode',method='html') for child in region if child.tag not in ('script','style'))
        if len(content)<20:raise RuntimeError('Museum real section content missing '+path)
        original_links=[{'label':' '.join(x.text_content().split()),'href':x.get('href')} for x in region.xpath('.//a[@href]')]
        copied.append({'path':path,'source_url':SOURCE+path,'title':title,
          'html':content,'html_sha256':hashlib.sha256(content.encode()).hexdigest(),
          'source_page_sha256':record['sha256'],'source_record':'official-remaining-original-sections.json',
          'image_links':[], 'link_count':len(original_links),'source_links':original_links,
          'captured_at':'2026-10-18'})
        print('DIRECTLY_VERIFIED_MUSEUM_OLD_INDEX',path,'title',title,'body_bytes',len(content),'links',len(original_links),flush=True)
    out={'source':SOURCE,'count':len(copied),'pages':copied}
    OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return out
if __name__=='__main__':parse()
