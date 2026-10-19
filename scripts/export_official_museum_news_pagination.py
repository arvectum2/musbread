#!/usr/bin/env python3
"""Source-authentic Drupal /novosty?page=1..27 archive query preserving SEO.

Next static export cannot serve different HTML based on query. Generate 27
independent static HTML index files and a local Nginx `$arg_page` map.
Every old archive page supplies exactly 10 source-verified original articles
with original text and exact original canonical (`/novosty`, not ?page=N).
Never redirect a page number to an unrelated news decade/category, never
construct content out of nonmuseum / random URLs, never touch public DNS.
"""
from __future__ import annotations
from pathlib import Path
from html import escape
from hashlib import sha256
from lxml import html as lx
from urllib.parse import urlsplit
import json,os,re
ROOT=Path(__file__).resolve().parents[1]
WEB=ROOT/'apps/web'
SRC=WEB/'src/data'
OUT=WEB/'out'
PRIVATE=ROOT/'.local_archive/official-site-originals'
MAP=ROOT/'deploy/nginx/museum_news_original_query_pages.map.conf'
CONF=ROOT/'deploy/nginx/museum_news_original_query_pages.server.conf'
REPORT=ROOT/'docs/seo/ORIGINAL_MUSEUM_NEWS_PAGINATION_PRESERVATION_20261018.md'
SOURCE='https://muzei-xleb.ru'


def source_pages():
    latest=json.loads((SRC/'official-museum-news.json').read_text(encoding='utf-8'))
    archived=json.loads((SRC/'official-museum-news-archive.json').read_text(encoding='utf-8'))
    if latest.get('source')!=SOURCE or archived.get('source')!=SOURCE or len(latest.get('articles',[]))!=10 or archived.get('count')!=270 or len(archived.get('indices',[]))!=27:
        raise RuntimeError('Original museum 28 archive index pages source ledger incomplete')
    if any(i['url']!=SOURCE+'/novosty?page='+str(n) for n,i in enumerate(archived['indices'],1)):
        raise RuntimeError('Original museum archive index order changed from canonical URL corpus')
    records={a['source_url'].removeprefix(SOURCE):a for a in latest['articles']+archived['articles']}
    if len(records)!=280 or any(sha256(a['html'].encode()).hexdigest()!=a['html_sha256'] for a in records.values()):
        raise RuntimeError('Original museum archive articles are not 280 distinct sha-locked original pages')
    if sha256(latest['index_html'].encode()).hexdigest()!=latest['index_html_sha256']:
        raise RuntimeError('Latest official museum index original source HTML hash mismatch')
    from_first=lx.fragment_fromstring(latest['index_html'],create_parent='div').xpath('.//a[@href]')
    first=[]
    for a in from_first:
        parsed=urlsplit(a.get('href',''))
        href=parsed.path if parsed.scheme=='https' and parsed.netloc=='muzei-xleb.ru' else a.get('href','')
        if re.fullmatch(r'/novosty/\d{4}-\d{2}-\d{2}/[a-z0-9-]+',href) and href not in first:
            first.append(href)
    if len(first)!=10 or set(first)!={a['path'] for a in latest['articles']}:
        raise RuntimeError('First page genuine museum archive article order is not source-backed')
    result=[(0,first,latest['index_html_sha256'])]
    for page,index in enumerate(archived['indices'],1):
        original=PRIVATE/f'news-list-page-{page}-20261018.html'
        if not original.is_file():raise RuntimeError('Original museum page snapshot missing '+str(original))
        raw=original.read_bytes()
        if sha256(raw).hexdigest()!=index['source_listing_sha256']:
            raise RuntimeError('Source HTML changed or corrupted for news index page '+str(page))
        tree=lx.fromstring(raw)
        canonical=tree.xpath('//link[@rel="canonical"]/@href')
        if canonical!=[SOURCE+'/novosty']:
            raise RuntimeError('Old museum source index has unexpected SEO canonical on page '+str(page))
        view=tree.xpath('//*[contains(concat(" ",normalize-space(@class)," ")," view-content ")]')
        if len(view)!=1:raise RuntimeError('Source museum news archive page has no unique view-content')
        hrefs=[]
        for anchor in view[0].xpath('.//a[@href]'):
            link=anchor.get('href','')
            if re.fullmatch(r'/novosty/\d{4}-\d{2}-\d{2}/[a-z0-9-]+',link) and link not in hrefs:
                hrefs.append(link)
        if hrefs!=index['article_paths'] or len(hrefs)!=10:
            raise RuntimeError('Original museum page news URLs/order do not match saved hashes '+str(page))
        for path in hrefs:
            if path not in records or records[path].get('archive_index_page')!=page:
                raise RuntimeError('Original museum news detail does not match archived page '+str(page))
        result.append((page,hrefs,index['source_listing_sha256']))
    if len({p for _,paths,_ in result for p in paths})!=280:
        raise RuntimeError('Original museum pagination loses or duplicates archived article links')
    return result,records


def emit():
    pages,records=source_pages()
    first=OUT/'novosty/index.html'
    if not first.is_file():raise RuntimeError('Build original Next site first')
    htmltree=lx.fromstring(first.read_bytes())
    assets=htmltree.xpath('//link[@rel="stylesheet"]/@href')
    if not assets or any(not (OUT/item.lstrip('/')).is_file() for item in assets):
        raise RuntimeError('Missing museum locally bundled stylesheet')
    # Strict legacy page references ONLY original museum news article paths.
    folder=OUT/'__museum_legacy_pager';folder.mkdir(parents=True,exist_ok=True)
    photos={}
    for name in ['official-museum-photo-assets.json','official-news-index-photo-assets.json',
       'official-deep-news-image-assets.json','official-historical-exhibition-image-assets.json']:
        photo=json.loads((SRC/name).read_text(encoding='utf-8'))
        for url,asset in photo['photos'].items():
            local=asset['path']
            if not (re.fullmatch(r'/media/museum-source/[a-f0-9]{64}\.webp',local)
                    and (OUT/local.lstrip('/')).is_file()):
                raise RuntimeError('Museum photo source is not locally self hosted '+url)
            photos[url]=local
    preview=os.environ.get('MUSBREAD_SITE_APPROVED')!='true' or os.environ.get('MUSBREAD_RELEASE_HOST')!='muzei-xleb.ru'
    robots='noindex,nofollow' if preview else 'noindex,follow'
    stylesheet=''.join(f'<link rel="stylesheet" href="{escape(uri,quote=True)}">' for uri in assets)
    for page,article_paths,_ in pages[1:]:
        cards=[]
        for path in article_paths:
            a=records[path]
            img=[]
            for original in a.get('image_links',[])[:2]:
                url=original['url'];local=photos.get(url)
                if local:
                    img.append('<img src="'+escape(local,quote=True)+'" alt="'+escape(original.get('alt') or a['title'],quote=True)+'" loading="lazy">')
            title=escape(a['title'])
            date=escape(a['published_on'])
            date_fmt='.'.join(reversed(date.split('-')))
            intro=escape(a.get('intro',''))
            cards.append('<article class="official-museum-program-card" data-original-museum-archive-item="'+escape(path,quote=True)+'">'
                +'<p class="official-museum-program-number">'+date_fmt+'</p>'
                +'<h2><a href="'+escape(path+'/',quote=True)+'">'+title+'</a></h2>'
                +''.join(img)
                +(f'<p>{intro}</p>' if intro else '')
                +'<p><a class="text-link" href="'+escape(path+'/',quote=True)+'">Читать оригинальную новость →</a></p></article>')
        pager=[]
        for n in range(28):
            link='/novosty' if n==0 else '/novosty?page='+str(n)
            text=str(n+1)
            pager.append('<strong aria-current="page">'+text+'</strong>' if n==page
                         else '<a href="'+link+'">'+text+'</a>')
        oldurl=SOURCE+'/novosty?page='+str(page)
        markup='<!doctype html><html lang="ru"><head><meta charset="utf-8">'
        markup+='<meta name="viewport" content="width=device-width,initial-scale=1">'
        markup+='<meta name="robots" content="'+robots+'">'
        markup+='<title>Новости — Санкт-Петербургский музей Хлеба. Страница '+str(page+1)+'</title>'
        markup+='<link rel="canonical" href="'+SOURCE+'/novosty">'
        markup+=stylesheet+'</head><body><header class="site-header">'
        markup+='<nav aria-label="Основная навигация"><a href="/">Музей Хлеба</a> · <a href="/novosty">Новости</a></nav></header>'
        markup+='<main id="main" class="section inner-page" data-original-museum-news-page="'+str(page)+'">'
        markup+='<nav aria-label="Хлебные крошки"><a href="/">Главная</a> / <a href="/novosty">Новости</a></nav>'
        markup+='<h1>Новости</h1><p>Архив публикаций музея · страница '+str(page+1)+' из 28</p>'
        markup+='<div class="official-museum-program-grid">'+''.join(cards)+'</div>'
        markup+='<nav aria-label="Страницы архива новостей" class="museum-news-original-pagination"><div class="museum-news-original-pagination-links">'+''.join(pager)+'</div></nav>'
        markup+='</main></body></html>\n'
        # TZ-207: WebKit macOS must be able to Tab through all pagination
        # links even without changing OS/Safari settings. Generated HTML is
        # ours (not original museum bytes), so preserve URLs and add focus.
        markup=markup.replace('<a ', '<a tabindex="0" title="Открыть материал или страницу архива новостей" ')
        dest=folder/f'page-{page}.html'
        dest.write_text(markup,encoding='utf-8')
        # Must remain standalone STATIC HTML, not a copy of latest list.
        doc=lx.fromstring(markup)
        if (len(doc.xpath('//article[@data-original-museum-archive-item]'))!=10
            or doc.xpath('//link[@rel="canonical"]/@href')!=[SOURCE+'/novosty']
            or len(doc.xpath('//a[@href="/novosty"]'))<1
            or len(doc.xpath('//script'))!=0):
            raise RuntimeError('Incorrect local museum historical archive index HTML '+str(page))
    rules=['# Verified museum original query URL pagination; only include in nginx HTTP context.',
           '# source: 27 original sha-locked old Drupal index HTML snapshots, 270 original articles.',
           'map $arg_page $musbread_original_news_index_file {',
           '    default "/novosty/index.html";']
    for n in range(1,28):rules.append(f'    {n} "/__museum_legacy_pager/page-{n}.html";')
    rules.append('}')
    MAP.parent.mkdir(parents=True,exist_ok=True)
    MAP.write_text('\n'.join(rules)+'\n',encoding='utf-8')
    CONF.write_text('''# Original museum public news index, including all ?page=1..27 variants.
# Include inside the museum Nginx server. Neither route redirects nor loops.
# The map $musbread_original_news_index_file must be included in http scope.
location = /novosty {
    try_files $musbread_original_news_index_file =404;
}
location = /novosty/ {
    try_files $musbread_original_news_index_file =404;
}
''',encoding='utf-8')
    REPORT.write_text(f'''# CP-SEO-04 · восстановление настоящей пагинации новостей · 18.10.2026

**Статус: подготовлено, не применено на живом сайте, SEO NO-GO.**

На действующем музее есть **28 разных индексных страниц**: `/novosty` (последние десять) и **27 архивных** `/novosty?page=1`–`?page=27` (270 исторических публикаций). Исходные байты всех архивных HTML сохранены приватно на Mac mini, их SHA-256 и порядок десяти ссылок проверены по `official-museum-news-archive.json`. Все **280/280 оригинальных новостей имеют самостоятельные исходные URL** в локальной сборке. У настоящего Drupal архивные индексные страницы имеют одинаковый `<link rel="canonical" href="https://muzei-xleb.ru/novosty">` — **это сохранено и не заменено на новые SEO-дубли**.

**Подготовленные файлы:** `apps/web/out/__museum_legacy_pager/page-1.html` … `page-27.html`; каждое HTML содержит **строго десять проверенных подлинных названий, дат и ссылок** из соответствующего исходного списка. Вся доступная локальная фотопривязка используется напрямую как WebP, ссылки на старый Drupal для загрузки изображений не нужны. Главный `/novosty` содержит собственные последние новости и навигацию по 28 страницам.

**Nginx:** [точная таблица для `$arg_page`](../../deploy/nginx/museum_news_original_query_pages.map.conf) + [два `location = /novosty`/`/novosty/`](../../deploy/nginx/museum_news_original_query_pages.server.conf). Старые query URL **не редиректятся**, а открывают свой самостоятельный статический HTML `200`. Случайный `?page=999` обрабатывается базовой страницей; итоговое поведение неутверждённых чисел нужно проверить отдельно на боевом веб-сервере. Поскольку backend статический, нельзя получить корректную пагинацию из `Next.js out/` без указанных правил Nginx — **это обязательная зависимость боевого cutover.**

**SEO-безопасность:** публичная публикация отключена до отдельного двойного разрешения `MUSBREAD_SITE_APPROVED=true` **и** `MUSBREAD_RELEASE_HOST=muzei-xleb.ru`; в текущей локальной сборке все 27 страниц имеют `noindex,nofollow`. Старый canonical на `/novosty`, а не на произвольно введённый `/news/archive/` и не на новый домен. Пробная XML-карта сайта по-прежнему пустая, robots.txt блокирует всю тестовую площадку. Перед сменой DNS проверить реальный HTTP 200 по всем 27 `?page=N`, href следующих страниц, старую нумерацию и точный canonical в живом Nginx, затем сверить поисковую аналитику Яндекса и Google.

**Вне охвата:** другие произвольные параметры Drupal, `www`/без `www`, выбор индексируемого основного хоста, боевой `nginx -t` и полная статистика индексации. Не применять на сервере музея без договора и приёмки.
''',encoding='utf-8')
    print('VERIFIED_ORIGINAL_MUSEUM_NEWS_PAGINATION',len(pages),'unique source pages',len(pages)*10,'genuine original detail links',len(pages)-1,'preserved query pages',flush=True)
    return pages
if __name__=='__main__':emit()
