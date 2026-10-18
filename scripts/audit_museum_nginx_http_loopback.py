#!/usr/bin/env python3
"""Real HTTP request integration test against ISOLATED loopback Nginx only.

Never touches the real museum, DNS or production Nginx. Takes a running HTTP
server bound to 127.0.0.1; defaults to port 18088. Verifies actual HTTP codes,
relative Location, source-exact canonical, 27 query pages, 101 real documents,
303 private-static WebP and no 301 chains across all 881 rules.
"""
from __future__ import annotations
import concurrent.futures as cf
import http.client,hashlib,json,os,re,sys
from pathlib import Path
from lxml import html
from urllib.parse import urlsplit
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from audit_museum_nginx_redirect_graph import MAP_RULE
from build_museum_legacy_page_aliases import build_map
from export_official_museum_original_documents import source_documents
from export_official_museum_news_pagination import source_pages
DATA=ROOT/'apps/web/src/data'
HOST='127.0.0.1'
PORT=int(os.environ.get("MUSBREAD_NGINX_PORT","18088"))
if not 1024<=PORT<=65535:raise RuntimeError("Loopback preflight needs a non-privileged local port")

def query(path:str,method:str='HEAD'):
    if not path.startswith('/') or 'http:' in path or 'https:' in path:
        raise ValueError('Loopback audit only permits original-site relative paths')
    c=http.client.HTTPConnection(HOST,PORT,timeout=12)
    try:
        c.request(method,path,headers={'Host':'muzei-xleb.ru','User-Agent':'MusBread-local-Nginx-preflight/1.0'})
        response=c.getresponse()
        data=response.read()
        return response.status,dict((key.lower(),value) for key,value in response.getheaders()),data
    finally:
        c.close()

def checked(workers=12):
    status,headers,data=query('/robots.txt','GET')
    if status!=200 or b'Disallow: /' not in data:
        raise RuntimeError('Loopback Nginx is not serving the private noindex museum static site')
    if headers.get('x-musbread-local-test')!='isolated':
        raise RuntimeError('Refusing to audit any web server without unique local-isolation header')
    static=json.loads((ROOT/'docs/seo/SEO_READINESS_AUDIT_SUMMARY_20261018.json').read_text())
    redirects=[match.groups() for line in (ROOT/'deploy/nginx/legacy_museum_redirects.map.conf').read_text().splitlines() if (match:=MAP_RULE.fullmatch(line))]
    assert len(redirects)==881
    failures=[];counter={'redirects':0,'redirect_targets_ok':0,'native_pages':0,'documents':0,'unique_webp':0,'archive_query_pages':0,'source_failures_still_missing':0}
    def redirect_test(pair):
        original,target=pair
        code,h,_=query(original)
        if code!=301 or h.get('location')!=target:
            return 'redirect',original,f'expected 301 Location {target!r}, got {code} {h.get("location")!r}'
        code2,h2,_=query(target)
        if code2!=200:
            return 'redirect',original,f'target must be direct 200, got {code2} for {target}'
        return 'redirect',original,None
    with cf.ThreadPoolExecutor(max_workers=workers) as pool:
        for kind,path,error in pool.map(redirect_test,redirects):
            if error:failures.append((kind,path,error))
            else:
                counter['redirects']+=1;counter['redirect_targets_ok']+=1
    if failures:raise RuntimeError('Real nginx 301/target failures '+repr(failures[:12]))
    sources=build_map()
    original_paths=sorted(path for path,item in sources.items() if item['why']!='source-verified-drupal-node')
    assert len(original_paths)==467
    def original_page(old):
        code,h,data=query(old,'GET')
        if code!=200:return 'page',old,'not a direct 200: '+str(code)
        doc=html.fromstring(data)
        target='https://muzei-xleb.ru'+old
        if doc.xpath('//link[@rel="canonical"]/@href')!=[target]:
            return 'page',old,'original canonical missing or duplicated: '+str(doc.xpath('//link[@rel="canonical"]/@href'))
        robots=doc.xpath('//meta[@name="robots"]/@content')
        if len(robots)!=1 or 'noindex' not in robots[0].lower():
            return 'page',old,'preview inadvertently indexable: '+str(robots)
        if doc.xpath('//meta[@http-equiv="refresh"]'):
            return 'page',old,'unexpected meta-refresh in native original page'
        return 'page',old,None
    with cf.ThreadPoolExecutor(max_workers=workers) as pool:
        for kind,path,error in pool.map(original_page,original_paths):
            if error:failures.append((kind,path,error))
            else:counter['native_pages']+=1
    if failures:raise RuntimeError('Real nginx original HTML regression '+repr(failures[:12]))
    docs=source_documents()
    assert len(docs)==101
    def document_check(entry):
        old,info=entry
        code,h,_=query(old)
        length=int(h.get('content-length','-1'))
        if code!=200 or length!=info['size_bytes']:
            return 'document',old,f'wrong status / byte length {code}/{length}, wanted 200/{info["size_bytes"]}'
        return 'document',old,None
    with cf.ThreadPoolExecutor(max_workers=workers) as pool:
        for kind,path,error in pool.map(document_check,list(docs.items())):
            if error:failures.append((kind,path,error))
            else:counter['documents']+=1
    if failures:raise RuntimeError('Real nginx old PDF/DOCX path regression '+repr(failures[:12]))
    media=sorted((ROOT/'apps/web/out/media/museum-source').glob('*.webp'))
    assert len(media)==303
    def photo_check(path):
        rel='/media/museum-source/'+path.name
        code,h,_=query(rel)
        if code!=200 or int(h.get('content-length','-1'))!=path.stat().st_size or 'image/webp' not in h.get('content-type',''):
            return 'webp',rel,f'wrong status / content type / byte length {code}/{h.get("content-type")}/{h.get("content-length")}'
        return 'webp',rel,None
    with cf.ThreadPoolExecutor(max_workers=workers) as pool:
        for kind,path,error in pool.map(photo_check,media):
            if error:failures.append((kind,path,error))
            else:counter['unique_webp']+=1
    if failures:raise RuntimeError('Real nginx media path regression '+repr(failures[:12]))
    pages,records=source_pages()
    assert len(pages)==28
    seen_hashes=set()
    for page,paths,_ in pages[1:]:
        code,h,data=query('/novosty?page='+str(page),'GET')
        if code!=200:failures.append(('archive',page,'not 200: '+str(code)));continue
        tree=html.fromstring(data)
        found=tree.xpath('//article[@data-original-museum-archive-item]/@data-original-museum-archive-item')
        canonical=tree.xpath('//link[@rel="canonical"]/@href')
        if found!=paths or canonical!=['https://muzei-xleb.ru/novosty']:
            failures.append(('archive',page,'not real old museum list or source canonical'))
        sha=hashlib.sha256(data).hexdigest()
        if sha in seen_hashes:failures.append(('archive',page,'two old query pages have identical HTML'))
        seen_hashes.add(sha);counter['archive_query_pages']+=1
    if failures:raise RuntimeError('Real nginx Drupal query page mismatch '+repr(failures[:12]))
    code,_,data=query('/novosty','GET')
    root=html.fromstring(data)
    links=root.xpath('//nav[@aria-label="Страницы архива новостей музея"]//a/@href')
    if code!=200 or links!=['/novosty?page='+str(x) for x in range(1,28)]:
        raise RuntimeError('Original news root index or 27 public query page links broken')
    # Museum originals unavailable at source: the new site must not invent content.
    missing=['/node/462','/obratnaya-svyaz','/sites/default/files/page/202110271242-prikaz_no94.pdf']
    for old in missing:
        code,_,_=query(old)
        if code!=404:failures.append(('original-source-unavailable',old,'expected safe 404, got '+str(code)))
        else:counter['source_failures_still_missing']+=1
    if failures:raise RuntimeError('Real nginx invented content for missing source '+repr(failures))
    code,_,data=query('/sitemap.xml','GET')
    if code!=200 or b'<url>' in data:
        raise RuntimeError('Unapproved site leaked sitemap URLs in nginx preview')
    counter['preview_disallow_all']=True
    counter['preview_sitemap_empty']=True
    counter['release_status']='LOCAL_LOOPBACK_HTTP_VERIFIED__PRODUCTION_NO_GO'
    return counter
if __name__=='__main__':
    result=checked()
    print('MUSBREAD_REAL_NGINX_LOOPBACK_HTTP_RESULT '+json.dumps(result,ensure_ascii=False,sort_keys=True),flush=True)
