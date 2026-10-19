"""Protect original /novosty?page=N archive lists and old canonical SEO.

The source Drupal pages all set canonical to /novosty. Preserve both exact
article memberships and canonical semantics without indexing 28 duplicates.
"""
from __future__ import annotations
from pathlib import Path
from lxml import html
import hashlib,re,sys,unittest,json
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from export_official_museum_news_pagination import source_pages,emit

class MuseumLegacyNewsPaginationTests(unittest.TestCase):
 def test_all_28_source_original_listings_have_distinct_known_ten_articles(self):
  pages,details=source_pages()
  self.assertEqual(len(pages),28)
  self.assertEqual(len(details),280)
  self.assertEqual([p[0] for p in pages],list(range(28)))
  allpaths=[path for _,paths,_ in pages for path in paths]
  self.assertEqual(len(allpaths),280)
  self.assertEqual(len(set(allpaths)),280)
  self.assertEqual(set(allpaths),set(details))
  self.assertEqual(len({tuple(paths) for _,paths,_ in pages}),28)
  self.assertTrue(all(len(paths)==10 for _,paths,_ in pages))

 def test_local_27_pages_include_the_same_source_links_in_same_order_and_no_duplicate_canonical(self):
  pages,details=source_pages()
  root=ROOT/'apps/web/out'
  for page,paths,_ in pages[1:]:
   with self.subTest(page=page):
    f=root/'__museum_legacy_pager'/f'page-{page}.html'
    self.assertTrue(f.is_file(),f)
    text=f.read_text()
    tree=html.fromstring(text)
    self.assertEqual(tree.xpath('//link[@rel="canonical"]/@href'),['https://muzei-xleb.ru/novosty'])
    self.assertEqual(tree.xpath('//meta[@name="robots"]/@content'),['noindex,nofollow'])
    self.assertEqual(tree.xpath('//main/@data-original-museum-news-page'),[str(page)])
    items=tree.xpath('//article[@data-original-museum-archive-item]')
    self.assertEqual(len(items),10)
    self.assertEqual([x.get('data-original-museum-archive-item') for x in items],paths)
    for item,old in zip(items,paths):
     self.assertEqual(item.xpath('./h2/a/@href'),[old+'/'])
     self.assertEqual(' '.join(item.xpath('./h2/a')[0].text_content().split()),details[old]['title'])
    self.assertEqual(tree.xpath('//script'),[])
    self.assertTrue(all(a.get('tabindex')=='0' for a in tree.xpath('//a[@href]')))
    self.assertEqual(tree.xpath('//a[starts-with(@href,"https://muzei-xleb.ru/sites/default/files/")]'),[])
    styles=tree.xpath('//link[@rel="stylesheet"]/@href')
    self.assertTrue(styles)
    self.assertTrue(all((root/x.lstrip('/')).is_file() for x in styles))
    pager=tree.xpath('//nav[@aria-label="Страницы архива новостей"]')
    self.assertEqual(len(pager),1)
    self.assertEqual(len(pager[0].xpath('.//a'))+len(pager[0].xpath('.//strong[@aria-current="page"]')),28)
    self.assertEqual(pager[0].xpath('.//strong[@aria-current="page"]/text()'),[str(page+1)])

 def test_original_first_page_news_has_27_live_query_links_and_its_own_exact_canonical(self):
  root=ROOT/'apps/web/out/novosty/index.html'
  t=html.fromstring(root.read_bytes())
  self.assertEqual(t.xpath('//link[@rel="canonical"]/@href'),['https://muzei-xleb.ru/novosty'])
  self.assertEqual(len(t.xpath('//nav[@aria-label="Страницы архива новостей музея"]')),1)
  links=t.xpath('//nav[@aria-label="Страницы архива новостей музея"]//a/@href')
  self.assertEqual(links,[f'/novosty?page={n}' for n in range(1,28)])
  self.assertEqual(t.xpath('//meta[@name="robots"]/@content'),['noindex, nofollow'])

 def test_nginx_prepared_exact_query_page_files_not_301_and_excludes_unknown_urls(self):
  mapfile=ROOT/'deploy/nginx/museum_news_original_query_pages.map.conf'
  server=ROOT/'deploy/nginx/museum_news_original_query_pages.server.conf'
  m=mapfile.read_text()
  self.assertIn('map $arg_page $musbread_original_news_index_file {',m)
  self.assertIn('    default "/novosty/index.html";',m)
  rows=re.findall(r'^    (\d+) "(/__museum_legacy_pager/page-\d+\.html)";$',m,re.M)
  self.assertEqual(rows,[(str(n),f'/__museum_legacy_pager/page-{n}.html') for n in range(1,28)])
  self.assertNotIn('return 301',server.read_text())
  self.assertIn('location = /novosty {',server.read_text())
  self.assertIn('location = /novosty/ {',server.read_text())
  self.assertEqual(server.read_text().count('try_files $musbread_original_news_index_file =404;'),2)
  self.assertNotIn('?page=',(ROOT/'deploy/nginx/legacy_museum_redirects.map.conf').read_text())
  for page,path in rows:self.assertTrue((ROOT/'apps/web/out'/path.lstrip('/')).is_file())

 def test_rebuild_is_idempotent_and_does_not_issue_http_or_change_original_urls(self):
  base=ROOT/'apps/web/out/__museum_legacy_pager'
  before={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in base.glob('page-*.html')}
  self.assertEqual(len(before),27)
  emit()
  after={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in base.glob('page-*.html')}
  self.assertEqual(before,after)

if __name__=='__main__':unittest.main()
