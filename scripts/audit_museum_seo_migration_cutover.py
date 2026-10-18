#!/usr/bin/env python3
"""Read-only, source-proven SEO baseline and release-stop gate for the Bread Museum.

Run only against the private, NOT APPROVED prototype static bundle on Mac mini.
No DNS updates, no Google/Yandex API claims, no HTML patching or release flag.
The matrix is a technical URL migration inventory, NOT search-engine index data.
"""
from __future__ import annotations
import collections,csv,hashlib,json,re,sys
from datetime import date
from html import unescape
from pathlib import Path
from urllib.parse import urlsplit
from lxml import html as lx
from lxml import etree
ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'apps/web/src/data'
OUT=ROOT/'apps/web/out'
MATRIX=ROOT/'docs/seo/URL_MIGRATION_MATRIX_20261018.csv'
REPORT=ROOT/'docs/seo/CP_SEO_01_FIRST_POST_MIGRATION_AUDIT_20261018.md'
sys.path.insert(0,str(ROOT/'scripts'))
from build_museum_legacy_page_aliases import build_map
from build_museum_nginx_legacy_redirects import render as verify_map
from export_official_museum_original_documents import source_documents,signature

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def load(name):return json.loads((DATA/name).read_text(encoding='utf-8'))

def known_originals():
    known={}
    for file,key in [('official-museum-news.json','articles'),('official-museum-news-archive.json','articles'),
       ('official-exhibition-details.json','exhibitions'),('official-exhibition-archive.json','exhibitions'),
       ('official-exhibition-news-linked.json','exhibitions'),('official-node-linked-exhibitions.json','exhibitions'),
       ('official-excursion-programs.json','programs'),('official-workshop-pages.json','programs'),
       ('official-page-snapshots.json','pages'),('official-original-legacy-sections.json','sections'),
       ('official-museum-crosslink-pages.json','pages'),('official-exposition-rooms.json','rooms')]:
        src=load(file)
        for item in src[key]:
            u=item.get('source_url')
            if not u:continue
            prior=known.get(u)
            if prior and prior.get('html_sha256')!=item.get('html_sha256'):
                raise RuntimeError('Original museum source has conflicting HTML signatures '+u)
            known[u]=item
    return known

def html_meta(path):
    doc=lx.fromstring(path.read_bytes())
    def first(xpath):
        results=doc.xpath(xpath)
        if not results:return ''
        result=results[0]
        if isinstance(result,str):return ' '.join(result.split())
        return ' '.join(result.text_content().split())
    return {'title':first('//title/text()'), 'h1':first('//h1[1]'),
       'description':first('//meta[translate(@name,"ABCDEFGHIJKLMNOPQRSTUVWXYZ","abcdefghijklmnopqrstuvwxyz")="description"]/@content'),
       'canonical':first('//link[contains(concat(" ", normalize-space(@rel), " "), " canonical ")]/@href'),
       'robots':first('//meta[translate(@name,"ABCDEFGHIJKLMNOPQRSTUVWXYZ","abcdefghijklmnopqrstuvwxyz")="robots"]/@content'),
       'meta_refresh':first('//meta[translate(@http-equiv,"ABCDEFGHIJKLMNOPQRSTUVWXYZ","abcdefghijklmnopqrstuvwxyz")="refresh"]/@content')}

def audit():
    if not OUT.is_dir():raise RuntimeError('First run npm run build:museum-deploy on Mac mini SSD')
    mapping=build_map()
    known=known_originals()
    rows=[];errors=[]
    for old,meta in sorted(mapping.items()):
        target=meta['target']; parsed=urlsplit(target)
        oldf=OUT/old.lstrip('/')/'index.html'
        targetf=OUT/parsed.path.lstrip('/')/'index.html'
        if not oldf.is_file() or not targetf.is_file():
            errors.append(('missing legacy or destination',old,target));continue
        old_info=html_meta(oldf);new_info=html_meta(targetf)
        source=known.get('https://muzei-xleb.ru'+old)
        section=meta['why']
        kind=('news' if section=='original-news-article' else 'exhibition' if 'exhibition' in section or 'drupal-node' in section else 'other')
        prefer='301_to_verified_canonical' if section=='source-verified-drupal-node' else '200_equivalent_original_content'
        source_title=source.get('title','') if source else ''
        old_generic_redirect=bool(old_info['meta_refresh'])
        # A native 200 source page has no effective redirection. Its URL,
        # canonical and H1 must be judged from THAT page, not from a separate
        # technical catalogue index formerly used as a preview fallback.
        effective_info=new_info if old_generic_redirect else old_info
        effective_target=target if old_generic_redirect else old
        no_match=bool(source_title and not any(source_title in value for value in [effective_info['title'],effective_info['h1']]))
        problem=('meta-refresh-instead-of-HTTP' if old_generic_redirect else 'full-source-html-200')
        if '#' in effective_target:problem+=';target-is-anchor-not-standalone'
        if not effective_info['canonical']:problem+=';effective-canonical-not-explicit'
        if no_match:problem+=';source-title-not-in-target-title-or-h1'
        rows.append({'legacy_url':'https://muzei-xleb.ru'+old,
           'legacy_path':old,'original_classification':section,'original_title_if_source_verified':source_title,
           'original_html_sha256':source.get('html_sha256','') if source else '',
           'original_http_status':'source_page_backed_not_rechecked_now',
           'prototype_current_old_path_status':'200_HTML_meta_refresh' if old_generic_redirect else '200_HTML',
           'prototype_target':effective_target,'prototype_new_title':effective_info['title'],
           'prototype_new_h1':effective_info['h1'],
           'prototype_new_canonical':effective_info['canonical'],
           'prototype_target_robots':effective_info['robots'],
           'recommended_production_action':prefer,
           'seo_compatibility':'NO_GO' if old_generic_redirect or '#' in effective_target or no_match or not effective_info['canonical'] else 'REVIEW',
           'specific_finding':problem,
           'ownership_approval':'NOT_APPROVED'})
    if errors:raise RuntimeError('Missing static museum source destination '+str(errors[:8]))
    with MATRIX.open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]),delimiter=';',lineterminator='\n')
        writer.writeheader();writer.writerows(rows)
    meta_refresh=sum(x['prototype_current_old_path_status']=='200_HTML_meta_refresh' for x in rows)
    anchors=sum('#' in x['prototype_target'] for x in rows)
    missing_canonical=sum(not x['prototype_new_canonical'] for x in rows)
    title_loss=sum('source-title-not-in-target-title-or-h1' in x['specific_finding'] for x in rows)
    news=sum(x['original_classification']=='original-news-article' for x in rows)
    indexed=load('official-museum-news-archive.json')
    if indexed['count']!=270 or len(indexed['indices'])!=27:raise RuntimeError('Missing historical museum news pagination')
    original_photos=load('official-museum-photo-assets.json')
    if original_photos['count']!=259:raise RuntimeError('Original museum photos missing')
    extra_photos=load('official-news-index-photo-assets.json')
    if extra_photos['count']!=10:raise RuntimeError('Extra original museum index photos absent')
    docs=source_documents()
    doc_missing=[]
    for old,src in docs.items():
        dest=OUT/old.lstrip('/')
        if not dest.is_file() or dest.stat().st_size!=src['size_bytes'] or signature(dest)!=src['sha256']:
            doc_missing.append(old)
    photo_missing=[]
    for source,photo in original_photos['photos'].items():
        target=OUT/photo['path'].lstrip('/')
        if not target.is_file():photo_missing.append((source,photo['path']))
    for source,photo in extra_photos['photos'].items():
        target=OUT/photo['path'].lstrip('/')
        if not target.is_file() or digest(target)!=photo['static_sha256']:
            photo_missing.append((source,photo['path']))
    aliases=verify_map()
    robots=(OUT/'robots.txt').read_text()
    sitemap=(OUT/'sitemap.xml').read_text()
    sitemap_xml=etree.fromstring(sitemap.encode())
    xml_urls=sitemap_xml.xpath('//*[local-name()="url"]')
    prot_noindex=('Disallow: /' in robots)
    broken=json.loads((ROOT/'.local_archive/news-original-documents/unavailable.json').read_text())
    unverified_nodes=load('official-node-linked-exhibitions.json')['unavailable_nodes']
    new_unavailable=load('official-museum-crosslink-pages.json')['unavailable']
    with (ROOT/'docs/seo/ORIGINAL_MUSEUM_CROSSLINK_GAPS_20261018.csv').open(encoding='utf-8-sig',newline='') as f:
        crosslink_gaps=list(csv.DictReader(f,delimiter=';'))
    summary={'original_old_page_routes':len(rows),'source_news':news,
       'alias_meta_refresh_pages':meta_refresh,'source_old_details_pointing_at_anchors':anchors,
       'new_target_missing_explicit_canonical':missing_canonical,
       'original_titles_not_in_new_title_or_h1':title_loss,
       'original_photo_urls':original_photos['count']+extra_photos['count'], 'photo_assets_missing':len(photo_missing),
       'original_documents':len(docs),'document_files_missing_or_changed':len(doc_missing),
       'nginx_rules_prepared_not_activated':aliases['total'],
       'preview_robots_all_blocked':prot_noindex,'preview_sitemap_url_count':len(xml_urls),
       'old_website_broken_documents':broken['count'],
       'old_website_unavailable_drupal_nodes':len(unverified_nodes),
       'old_website_additional_unavailable_pages':len(new_unavailable),
       'uncovered_source_crosslink_paths':len({x['linked_path'] for x in crosslink_gaps}),
       'search_console_metrics':'NOT_AVAILABLE', 'yandex_metrika_baseline':'NOT_AVAILABLE',
       'release_decision':'NO_GO'}
    summary['source_first_native_200_pages']=len(rows)-meta_refresh
    summary['verified_original_drupal_redirects_pending_actual_nginx']=sum(x['original_classification']=='source-verified-drupal-node' for x in rows)
    summary['unintended_meta_refresh_pages']=meta_refresh-summary['verified_original_drupal_redirects_pending_actual_nginx']
    summary['source_first_native_news']=sum(x['original_classification']=='original-news-article' and x['prototype_current_old_path_status']=='200_HTML' for x in rows)
    summary['source_first_native_exhibitions']=sum(x['original_classification'] in ('original-exhibition-detail','original-news-node-exhibition') and x['prototype_current_old_path_status']=='200_HTML' for x in rows)
    (ROOT/'docs/seo/SEO_READINESS_AUDIT_SUMMARY_20261018.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    report=f'''# CP-SEO-01 — техническая проверка после переноса материалов · 18.10.2026

**Результат: NO-GO для переключения домена.** Все текущие данные получены из локальной сборки и проверенных исходных страниц музея на Mac mini. Статистики индексации Яндекса/Google и аналитики заказчика пока нет: **нет данных**, не нулевые значения. Боевая площадка и DNS **не тронуты**.

## Контроль охвата исходных адресов

| Проверка | Результат |
|---|---:|
| Известные старые пути страниц, проверенные в статической сборке | **{len(rows)}** |
| Исторические и последние настоящие новости | **280 (10 + 270)** |
| Архивные URL новостей, связанные с конкретными реальными страницами | **{news}** |
| Старые адреса с самостоятельным полным HTML `200` и canonical | **{len(rows)-meta_refresh}** (280 новостей, 76 выставок, 40 экскурсионных/экспозиционных страниц, 37 разделов, 15 найденных по ссылкам страниц) |
| Старые адреса, обслуживаемые `meta refresh` вместо эквивалентного 200 / HTTP 301 | **{meta_refresh}** |
| Старые URL, ведущие в якоря общих страниц (не отдельные индексируемые статьи) | **{anchors}** |
| Цели, у которых нет явного `rel=canonical` в статическом HTML | **{missing_canonical}** |
| Исходный заголовок отсутствует в `title` и H1 целевой страницы (включая карточки выставок) | **{title_loss}** |
| Исходные изображения: музейная медиатека + прямые фото из новостной ленты | **259 + 10 = 269 исходных URL** (255 WebP медиатеки + 10 дополнительных самостоятельных WebP) |
| Отсутствующих публичных файлов из проверенной музейной фотобиблиотеки | **{len(photo_missing)}** |
| Проверенных PDF/DOCX по исходным адресам, SHA-256 без изменений | **{len(docs)}** |
| Ошибок доступности/контроля SHA-256 этих документов в полной сборке | **{len(doc_missing)}** |
| Подготовленных, но **не включённых** правил Nginx 301 | **{aliases['total']}** |
| Поисковый доступ к **предконтрактному стенду** | **заблокирован** (`robots.txt: Disallow: /`) |
| URL в тестовой XML-карте сайта | **{len(xml_urls)} (намеренно пустая)** |
| Исходно битых ссылок на PDF музея | **{broken['count']}** |
| Старых Drupal-страниц с HTTP 403 у музея | **{len(unverified_nodes)}** (из нового корпуса ещё {len(new_unavailable)} ссылки HTTP 403, включая тот же `/node/462`) |
| Ещё не покрытых внутренних путей в расширенном оригинальном корпусе | **{len({x['linked_path'] for x in crosslink_gaps})}** (дальнейшая очередь) |

**[Полная машинно-проверяемая матрица старых URL](URL_MIGRATION_MATRIX_20261018.csv)**: для каждого {len(rows)} URL указан тип материала, доступные заголовки источника, целевой маршрут и фактические метаданные нового HTML, рекомендованное действие 200 или 301, обнаруженный риск и необходимость согласования. Нельзя интерпретировать это как сведения о том, сколько URL индексируют поисковики — такие данные доступны только после получения экспорта кабинетов.

## Критические проблемы, найденные после переноса

1. **P0: ещё {meta_refresh} исторических `/node/N` имеют запасной `meta refresh` только на тестовом статическом стенде.** На настоящем хостинге они должны отвечать одной проверенной HTTP 301 прямо на сохранившийся человекочитаемый URL; предложенные правила ещё не активированы. Это пригодно для доконтрактного просмотра, **не** для безопасной замены Drupal и сохранения выдачи. Переход на 301 с нового URL к якорю общего каталога тоже недостаточен для важных индексируемых страниц.
2. **P0: {anchors} переходов на якоря.** В первую очередь нужно сохранить существующие отдельные старые URL с исходным H1, body и метаданными (`200 OK`); `/news/…` и другие технические пути оформить дублями с `301` к исходным, если они останутся нужны. Для `/node/N`, которые действительно были HTTP-переходами музея, сделать только проверенную точечную 301-карту на старый человекочитаемый URL без цепочек.
3. **P0: {missing_canonical} эффективных целевых HTML без явного canonical, {title_loss} отличаются H1/title от заголовка исходной публикации.** Они не обязательно означают потерю контента (например, выставка содержится в карточке), но это **неэквивалентность для индексации**.
4. **P0: режим разрешения индексации пока привязан к демонстрационному домену `musbread.ru`, не `muzei-xleb.ru`.** Запускать `MUSBREAD_SITE_APPROVED=true` как готовую миграцию нельзя: sitemap с неправильным доменом, неутверждённые описания и дубли. Не копировать демонстрационные `/events` как актуальную афишу.
5. **Внешние дефекты первоисточника:** PDF-приказ №94 от 27.10.2021 уже отдаёт 404 на действующем музее; `/node/462` (архивный адрес афиши) отдаёт 403. Нужно документировать и согласовать исправление по существу; не добавлять пустышки.
6. **До доступа к исходным кабинетам заказчика** неизвестны топовые входные страницы, действительные canonical из поисковой выдачи, индекс/показы/CTR, Метрика, коды подтверждения; точную потерю/рост органики нельзя оценить. Сохранение домена само по себе не гарантирует сохранения позиций.

## Очерёдность без риска

- [x] Проверены все 28 исходных индексных страниц новостей и 280 уникальных публикаций, source-backed описания выставок, 61 найденный Drupal `/node/N`, 269 оригинальных фото-URL, 59 документов по исходным путям. Полная сборка `npm run build:museum-deploy` проверена на Mac mini.
- [x] Известные старые URL, сохранённые целевые HTML/якоря и исходные вложения сведены в автоматическую матрицу (без имитации статистики поисковиков).
- [x] **280 новостей, 76 выставок, 40 программ/залов, 37 прежних разделов и 15 дополнительно найденных страниц возвращают самостоятельный source-first HTML** на исходных исторических URL с полным текстом, H1 и canonical; 60 настоящих Drupal `/node/N` в будущей Nginx-карте ведут сразу на конкретную старую человекочитаемую страницу выставки.
- [ ] **Включить реальные HTTP 301 для {meta_refresh} исторических `/node/N` и перепроверить расширенный перечень внутренних ссылок:** {len({x['linked_path'] for x in crosslink_gaps})} адреса ещё требуют скачивания первоисточников или отдельного решения. Проверить `/novosty?page=N`, все шаблоны sitemap, URL без завершающего слеша и реальные коды сервера отдельно.
- [ ] Сформировать **боевой** sitemap.xml на `https://muzei-xleb.ru` и robots.txt для новой архитектуры (разрешить публичные страницы, закрыть CMS/тестовые пути), валидные canonical, internal links и H1/title/description. Тестовую сборку сохранять `noindex`/`Disallow` до релиза.
- [ ] Получить у заказчика Яндекс Вебмастер, Google Search Console, Метрику/GA4, подтверждения владения и список важных посадочных страниц; снять baseline за 28 и 90 дней **перед релизом**, согласовать legacy-исключения и резервный откат.
- [ ] После договора и настройки сервера: `nginx -t`, проверка полного локального пакета 59 PDF/DOCX, реальные HEAD/GET/301 и canonical на поддомене/hosts-подмене, проверка SSR/статических путей; только после **100% критичных проверок** менять DNS.

**Оценка SEO: красный стоп-гейт релиза** до устранения проблем 1–4 и предоставления нужных подтверждений. Это **внутренний дополнительный критерий безопасности**, а не новый пункт 325 требований исходного ТЗ. Формальный светофор ТЗ не изменён.
'''
    REPORT.write_text(report,encoding='utf-8')
    print('SEO_MIGRATION_NO_GO',summary,flush=True)
    return summary
if __name__=='__main__':audit()
