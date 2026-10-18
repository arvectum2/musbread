#!/usr/bin/env python3
"""Museum exhibitions verified via OLD /node/N links in genuine news.

Preserve full original published HTML, not speculative text and never confuse
an archived exhibition with a currently bookable museum event. All original
Drupal nodes were individually resolved/downloaded via Mac mini first.
"""
from __future__ import annotations
import json,hashlib,re,collections
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import urlsplit
from lxml import html
from capture_official_museum_pages import parse
ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'apps/web/src/data'
PRIVATE=ROOT/'.local_archive/news-linked-nodes'
OUT=DATA/'official-node-linked-exhibitions.json'
DOMAIN='https://muzei-xleb.ru'
EXHIBITION=re.compile(r'^/vistavky/20\d{2}-\d\d-\d\d/[a-z0-9-]+$')

def main():
    news=[]
    for fname in ('official-museum-news.json','official-museum-news-archive.json'):
        data=json.loads((DATA/fname).read_text(encoding='utf-8'))
        if data['source']!=DOMAIN:raise RuntimeError('News source not original museum')
        news+=data['articles']
    source_referers=collections.defaultdict(list)
    for article in news:
        if hashlib.sha256(article['html'].encode()).hexdigest()!=article['html_sha256']:
            raise RuntimeError('Original linked news digest no longer valid')
        for a in html.fragment_fromstring(article['html'],create_parent='div').xpath('.//a[@href]'):
            u=urlsplit(a.get('href',''))
            if u.hostname=='muzei-xleb.ru' and re.fullmatch(r'/node/\d+',u.path):
                source_referers[u.path].append(article)
    originals=json.loads((PRIVATE/'manifest.json').read_text())
    if originals.get('source')!=DOMAIN or len(originals.get('nodes',[]))!=len(source_referers):
        raise RuntimeError('Not all original museum node links verified via Mac mini')
    past=set()
    for filename in ['official-exhibition-details.json','official-exhibition-archive.json','official-exhibition-news-linked.json']:
        data=json.loads((DATA/filename).read_text())
        past.update(x['source_url'] for x in data['exhibitions'])
    target_by_url={}
    verified=[];failures=[];unclassified=[]
    for record in originals['nodes']:
        path=record['path']
        if path not in source_referers:raise RuntimeError('Arbitrary unreferenced museum node')
        if record['status']!=200:
            failures.append({**record,'referring_news_count':len(source_referers[path])})
            continue
        final=urlsplit(record['resolved_url'])
        if final.scheme!='https' or final.hostname!='muzei-xleb.ru':
            raise RuntimeError('Museum linked node redirected to external URL')
        if not EXHIBITION.fullmatch(final.path):
            unclassified.append({**record,'referring_news_count':len(source_referers[path])})
            continue
        raw=(PRIVATE/(path.rsplit('/',1)[-1]+'.html')).read_bytes()
        if hashlib.sha256(raw).hexdigest()!=record['html_sha256']:
            raise RuntimeError('Original verified Drupal node bytes altered')
        parsed=parse(raw.decode('utf-8','replace'),final.path,datetime.now(timezone.utc).isoformat(timespec='seconds'),min_text_length=8)
        if parsed['title']!=record['original_title'] or parsed['source_url']!=record['resolved_url']:
            raise RuntimeError('Node final original museum exhibition mismatch')
        if record.get('html_canonical') and record['html_canonical']!=parsed['source_url']:
            raise RuntimeError('Drupal node page canonical differs from verified original')
        owner=source_referers[path][0]
        row={'node_path':path,'node_paths':[path],
             'source_url':parsed['source_url'],'path':final.path,
             'title':parsed['title'],'html':parsed['html'],
             'captured_utc':parsed['captured_utc'],
             'html_sha256':parsed['html_sha256'],
             'source_page_sha256':record['html_sha256'],
             'text_length':parsed['text_length'],
             'image_links':parsed['image_links'],
             'document_links':parsed['document_links'],
             'slug':'museum-exhibit-'+final.path.removeprefix('/vistavky/').replace('/','-'),
             'category_slug':'exhibitions-past',
             'intro':' '.join(html.fragment_fromstring(parsed['html'],create_parent='div').text_content().split())[:245],
             'linked_news_slug':owner['slug'],'linked_news_url':owner['source_url'],
             'linked_news_html_sha256':owner['html_sha256'],
             'photos_rights_confirmed':False}
        existing=target_by_url.get(parsed['source_url'])
        if existing:
            if existing['html_sha256']!=row['html_sha256']:
                raise RuntimeError('Two original nodes disagree on same exhibition contents')
            existing['node_paths'].append(path)
        else:
            target_by_url[row['source_url']]=row
        verified.append({'node_path':path,'source_url':row['source_url'],'exists_in_prior_catalogue':row['source_url'] in past})
    new=[x for x in target_by_url.values() if x['source_url'] not in past]
    copied=[x for x in target_by_url.values() if x['source_url'] in past]
    doc={'source':DOMAIN,'news_count':len(news),'node_count':len(source_referers),
         'verified_exhibition_node_count':len(verified),
         'new_exhibition_count':len(new),
         'existing_exhibition_count':len(copied),
         'unavailable_nodes':failures,'other_pages':unclassified,
         'verified_node_targets':verified,'exhibitions':new}
    OUT.write_text(json.dumps(doc,ensure_ascii=False,indent=2)+'\n')
    print('ORIGINAL_NEWS_NODE_EXHIBITIONS',doc['node_count'],'literal museum nodes',
          len(verified),'source-verified exhibit links',len(new),'previously unimported descriptions',
          len(copied),'already known',len(failures),'unavailable',len(unclassified),'other types',flush=True)
if __name__=='__main__':main()
