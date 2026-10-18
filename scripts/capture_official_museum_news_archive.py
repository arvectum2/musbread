#!/usr/bin/env python3
"""Capture genuine archive news from all source-verified museum index pages.

Original page listings are privately saved on ArvectumSSD. No placeholders,
images, event creation, PII or unlicensed media. Never overwrite latest news.
Respect the museum source 10s crawl delay between full original article GETs.
"""
from __future__ import annotations
import json,re
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from time import sleep
from lxml import html as lx
from capture_official_museum_pages import HOST,parse,safe_html,url
from capture_official_museum_news import fetch,NEWS_RE
from cache_official_museum_photos import canonical

ROOT=Path(__file__).resolve().parents[1]
INDICES=ROOT/'.local_archive/official-site-originals'
DEST=ROOT/'apps/web/src/data/official-museum-news-archive.json'
PRIVATE_CACHE=ROOT/'.local_archive/news-archive-verified-articles'
LATEST=ROOT/'apps/web/src/data/official-museum-news.json'

def parse_archival_article(raw:str,path:str,stamp:str)->dict:
    """Preserve genuinely image-only museum notices without inventing text/OCR."""
    try:
        detail=parse(raw,path,stamp,min_text_length=8)
        detail['image_only']=False
        return detail
    except ValueError:
        tree=lx.fromstring(raw)
        headers=tree.xpath('//h1')
        articles=tree.xpath('//article[contains(concat(" ",normalize-space(@class)," ")," node-novost ")]')
        if len(headers)!=1 or len(articles)!=1:
            raise RuntimeError('Not an identifiable original museum news article '+path)
        article=articles[0]
        if ' '.join(article.text_content().split()):
            raise RuntimeError('Unexpected unparsed text in original news '+path)
        image_nodes=article.xpath('.//img[@src]')
        if not 1<=len(image_nodes)<=8:
            raise RuntimeError('No real picture in image-only museum news '+path)
        photos=[]
        for image in image_nodes:
            candidate=image.getparent().get('href') if image.getparent().tag=='a' else image.get('src')
            original=canonical(url(candidate,HOST+path) or '')
            photos.append({'url':original,'alt':image.get('alt','')[:280]})
        empty=sha256(b'').hexdigest()
        return {'path':path,'source_url':HOST+path,
                'title':' '.join(headers[0].text_content().split()),
                'captured_utc':stamp,'html':'','html_sha256':empty,
                'text_sha256':empty,'text_length':0,
                'image_links':photos,'document_links':[],
                'image_only':True,'source_page_sha256':sha256(raw.encode('utf-8')).hexdigest()}

def main():
    latest=json.loads(LATEST.read_text(encoding='utf-8'))
    seen={p['source_url'] for p in latest['articles']}
    stamp=datetime.now(timezone.utc).isoformat(timespec='seconds')
    links=[];indices=[]
    for page in range(1,28):
        path=INDICES/f'news-list-page-{page}-20261018.html'
        raw=path.read_text(encoding='utf-8')
        tree=lx.fromstring(raw)
        view=tree.xpath('//*[contains(concat(" ",normalize-space(@class)," ")," view-content ")]')
        if len(view)!=1:raise RuntimeError('Museum archive listing structure changed')
        collected=[]
        for anchor in view[0].xpath('.//a[@href]'):
            url=anchor.get('href','')
            if not NEWS_RE.fullmatch(url) or url in collected:continue
            label=' '.join(anchor.text_content().split())
            if len(label)<3 or HOST+url in seen:raise RuntimeError('Duplicate or unnamed historical news')
            collected.append(url)
            links.append({'path':url,'title':label,'published_on':url.split('/')[2],
                          'source_url':HOST+url,'index_page':page})
            seen.add(HOST+url)
        if len(collected)!=10:
            raise RuntimeError(f'Museum archive index {page} has unexpected {len(collected)} source links')
        sanitized=safe_html(view[0],HOST+'/novosty?page='+str(page))
        indices.append({'url':HOST+'/novosty?page='+str(page),
                        'source_listing_sha256':sha256(raw.encode('utf-8')).hexdigest(),
                        'index_html_sha256':sha256(sanitized.encode('utf-8')).hexdigest(),
                        'article_paths':collected})
    if len(indices)!=27 or len(links)!=270 or len(links)!=sum(len(index['article_paths']) for index in indices):
        raise RuntimeError('Verified source index cardinality incorrect or incomplete')
    entries=[];last_request=False
    PRIVATE_CACHE.mkdir(parents=True,exist_ok=True)
    for n,meta in enumerate(links,1):
        archive_file=PRIVATE_CACHE/(meta['path'].rsplit('/',1)[-1]+'-'+meta['published_on']+'.json')
        if archive_file.exists():
            detail=json.loads(archive_file.read_text(encoding='utf-8'))
        else:
            if last_request:sleep(10)
            detail=parse_archival_article(fetch(meta['path']),meta['path'],stamp)
            last_request=True
        if(detail['title']!=meta['title'] or detail['source_url']!=meta['source_url']
           or (detail.get('image_only') is not True and detail['text_length']<8)
           or (detail.get('image_only') is True and (detail['html']!='' or not detail['image_links']))
           or sha256(detail['html'].encode()).hexdigest()!=detail['html_sha256']):
            raise RuntimeError('Unverified original historical article '+meta['path'])
        if not archive_file.exists():
            tmp=archive_file.with_suffix('.tmp')
            tmp.write_text(json.dumps(detail,ensure_ascii=False)+'\n',encoding='utf-8')
            tmp.replace(archive_file)
        body=' '.join(lx.fromstring('<div>'+detail['html']+'</div>').text_content().split())
        detail.update({'slug':'museum-news-'+meta['published_on']+'-'+meta['path'].rsplit('/',1)[-1],
                       'published_on':meta['published_on'],'intro':body[:245],
                       'photos_rights_confirmed':False,'archive_index_page':meta['index_page']})
        entries.append(detail)
        print('CAPTURED',n,'/',len(links),detail['title'][:67],len(body.split()),'words',flush=True)
    snapshot={'source':HOST,'snapshot_utc':stamp,'index_urls':[x['url'] for x in indices],
              'indices':indices,'count':len(entries),'articles':entries,
              'rights_note':'Original museum historical news: archival only, not upcoming event; photo rights unconfirmed.'}
    tmp=DEST.with_suffix('.json.tmp')
    tmp.write_text(json.dumps(snapshot,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    tmp.replace(DEST)
    print('ARCHIVE_NEWS_COMPLETE',len(entries),'original signed texts saved without photos',flush=True)

if __name__=='__main__':main()
