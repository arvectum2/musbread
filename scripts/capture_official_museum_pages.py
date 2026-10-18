#!/usr/bin/env python3
"""Reproducible, *manual* and rate-limited snapshot of public museum reference pages.

Sources are the actual HTML pages on muzei-xleb.ru. No speculative legal text,
no credentials, no external browser, no changing production CMS. Refresh only
when an operator explicitly runs this script from the configured Mac mini.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
from hashlib import sha256
from html import escape
from pathlib import Path
from time import sleep
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen
import json
import re
from lxml import html as lx

ROOT=Path(__file__).resolve().parents[1]
HOST='https://muzei-xleb.ru'
OUT=ROOT/'apps/web/src/data/official-page-snapshots.json'
TARGETS=[
    '/kontakty', '/administraciya',
    '/o-muzee', '/istoriya-zdaniya', '/ekspozicii', '/posetitelyam',
    '/stoimost', '/pushkinskaya-karta', '/informaciya-dlya-mgn',
    '/politika-konfidencialnosti-i-obrabotki-personalnyh-dannyh',
    '/oficialnye-dokumenty-muzeya', '/ceny-i-usloviya-predostavleniya-uslug',
    '/politika-obespecheniya-usloviy-dostupnosti-dlya-invalidov-i-drugih-mobilnyh-grazhdan',
    '/vakansii', '/finansovo-hozyaystvennaya-deyatelnost',
    '/protivodeystvie-korrupcii', '/my-ispolzuem-cookie',
]
SAFE={'p','br','strong','b','i','em','h2','h3','h4','ul','ol','li',
      'blockquote','a','table','thead','tbody','tr','td','th'}
VOID={'br'}
FILE_EXT=re.compile(r'\.(pdf|docx?|xlsx?|ods|rtf)(?:$|\?)',re.I)

def url(raw: str, base: str) -> str|None:
    if not raw or raw.startswith(('#','javascript:','data:','file:','//')):return None
    full=urljoin(base,raw)
    u=urlparse(full)
    if u.scheme not in ('http','https','mailto'):return None
    if u.scheme=='https' and u.netloc=='www.muzei-xleb.ru':
        full=full.replace('www.muzei-xleb.ru','muzei-xleb.ru',1)
    return full

def safe_html(element, base:str) -> str:
    parts=[]
    def visit(e):
        tag=str(e.tag).lower() if isinstance(e.tag,str) else ''
        allowed=tag in SAFE
        opening=''
        if allowed:
            if tag=='a':
                # Image-only anchors from Drupal views would become empty links
                # after stripping IMG. Do not create inaccessible empty links.
                if not ' '.join(e.text_content().split()): allowed=False
                dest=url(e.get('href',''),base)
                if dest:
                    opening='<a href="'+escape(dest,quote=True)+'">'
                else: allowed=False
            else:opening='<'+tag+'>'
        if allowed:parts.append(opening)
        if e.text:parts.append(escape(e.text))
        for child in e:
            if isinstance(child.tag,str) and child.tag.lower() not in ('script','style','form','iframe','noscript','svg'):
                visit(child)
            if child.tail:parts.append(escape(child.tail))
        if allowed and tag not in VOID:parts.append('</'+tag+'>')
    for child in element:
        visit(child)
        if child.tail:parts.append(escape(child.tail))
    return ''.join(parts).strip()

def parse(source:str,path:str,captured:str,min_text_length:int=30)->dict:
    root=lx.fromstring(source)
    headers=root.xpath('//h1')
    title=' '.join(headers[0].text_content().split()) if headers else ''
    body=root.xpath('//*[contains(concat(" ",normalize-space(@class)," ")," field-name-body ")]')
    if body:chosen=body[0]
    elif path == '/ekspozicii':
        # Gallery index, not a Drupal article: preserve its actual room links.
        views=root.xpath('//*[contains(concat(" ",normalize-space(@class)," ")," view-content ")]')
        if not views:raise ValueError('Official exposition index missing')
        chosen=views[0]
    else:
        # Some official indexes consist solely of document "field-item" links.
        items=root.xpath('//*[contains(concat(" ",normalize-space(@class)," ")," field-item ")]')
        if not items:raise ValueError('No identifiable Drupal body for '+path)
        chosen=lx.Element('div')
        for item in items[:60]:chosen.append(lx.fromstring(lx.tostring(item)))
    text=' '.join(chosen.text_content().split())
    doc_links={}
    for a in root.xpath('//a[@href]'):
        dest=url(a.get('href',''),HOST+path)
        if not dest or urlparse(dest).hostname not in ('muzei-xleb.ru','www.muzei-xleb.ru'):continue
        if FILE_EXT.search(urlparse(dest).path):
            doc_links[dest]=' '.join(a.text_content().split())[:280] or urlparse(dest).path.rsplit('/',1)[-1]
    images=[]
    for img in chosen.xpath('.//img[@src]'):
        dest=url(img.get('src',''),HOST+path)
        if dest and urlparse(dest).hostname in ('muzei-xleb.ru','www.muzei-xleb.ru'):
            images.append({'url':dest,'alt':img.get('alt','')[:280]})
    safe=safe_html(chosen,HOST+path)
    if len(text)<min_text_length:raise ValueError('Short or empty Drupal body '+path)
    return {
        'path':path, 'source_url':HOST+path, 'title':title,
        'captured_utc':captured, 'html':safe,
        'text_sha256':sha256(text.encode()).hexdigest(),
        'html_sha256':sha256(safe.encode()).hexdigest(),
        'text_length':len(text),
        'document_links':[{'url':u,'label':v} for u,v in doc_links.items()],
        'image_links':images,
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--output',type=Path,default=OUT)
    ap.add_argument('--delay',type=float,default=10.0)
    ap.add_argument('--max-pages',type=int,default=len(TARGETS))
    a=ap.parse_args()
    if a.delay<10:raise SystemExit('Museum robots.txt Crawl-delay: 10 must be respected')
    captured=datetime.now(timezone.utc).isoformat(timespec='seconds')
    pages=[]
    errors=[]
    for i,path in enumerate(TARGETS[:a.max_pages]):
        if i:sleep(a.delay)
        request=Request(HOST+path,headers={'User-Agent':'Mozilla/5.0 (MusBread reference content verifier; manual operation)','Accept':'text/html'})
        try:
            with urlopen(request,timeout=15) as response:
                content_type=response.headers.get('Content-Type','')
                if response.status!=200 or 'text/html' not in content_type:
                    raise ValueError(f'Unexpected response {response.status}: {content_type}')
                content=response.read(1_500_000).decode('utf-8','replace')
            record=parse(content,path,captured)
            pages.append(record)
            print('OK',len(pages),path,'chars',record['text_length'],'PDFs',len(record['document_links']),flush=True)
        except Exception as ex:
            errors.append({'path':path,'error':type(ex).__name__})
            print('FAIL',path,type(ex).__name__,flush=True)
    payload={'source':HOST,'snapshot_utc':captured,'count':len(pages),'pages':pages,'errors':errors}
    if len(pages)<max(3,a.max_pages//2):
        raise SystemExit('Insufficient verified source pages; refusing to replace snapshot')
    a.output.parent.mkdir(parents=True,exist_ok=True)
    temp=a.output.with_suffix('.json.tmp')
    temp.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n')
    temp.replace(a.output)
    print('SAVED',a.output,'pages',len(pages),'failed',len(errors),flush=True)

if __name__=='__main__':main()
