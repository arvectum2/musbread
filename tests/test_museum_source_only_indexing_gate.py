"""Double-approval SEO release must not index demo or change museum canonical."""
import json,re,unittest,sys
from pathlib import Path
from urllib.parse import urlsplit
from lxml import html
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from build_museum_legacy_page_aliases import build_map
from audit_museum_nginx_redirect_graph import preflight

class MuseumSeoApprovalNoRegressionTests(unittest.TestCase):
 def test_all_467_original_canonical_pages_stay_exact_and_noindex_in_preview(self):
  roots=build_map();source={path for path,v in roots.items() if v['why']!='source-verified-drupal-node'}
  self.assertEqual(len(source),467)
  for old in source:
   with self.subTest(old=old):
    page=ROOT/'apps/web/out'/old.lstrip('/')/'index.html'
    doc=html.fromstring(page.read_bytes())
    self.assertEqual(doc.xpath('//link[@rel="canonical"]/@href'),['https://muzei-xleb.ru'+old])
    robots=doc.xpath('//meta[@name="robots"]/@content')
    self.assertEqual(len(robots),1)
    self.assertIn('noindex',robots[0].lower())
    self.assertEqual(doc.xpath('//meta[@http-equiv="refresh"]'),[])

 def test_demo_routes_and_preview_robots_remain_closed_and_sitemap_empty(self):
  root=ROOT/'apps/web/out'
  self.assertEqual((root/'robots.txt').read_text().strip(),'User-Agent: *\nDisallow: /')
  sitemap=(root/'sitemap.xml').read_text()
  self.assertNotIn('<url>',sitemap)
  for name in ['guide/plan-visit/index.html','events/index.html','index.html']:
   p=root/name
   self.assertTrue(p.is_file(),name)
   document=html.fromstring(p.read_bytes())
   metarobots=document.xpath('//meta[@name="robots"]/@content')
   self.assertEqual(len(metarobots),1)
   self.assertIn('noindex',metarobots[0].lower())

 def test_go_live_sitemap_is_only_467_proven_originals_with_correct_host(self):
  data=ROOT/'apps/web/src/data'
  names=[('official-museum-news.json','articles'),('official-museum-news-archive.json','articles'),
   ('official-exhibition-details.json','exhibitions'),('official-exhibition-archive.json','exhibitions'),
   ('official-exhibition-news-linked.json','exhibitions'),('official-node-linked-exhibitions.json','exhibitions'),
   ('official-excursion-programs.json','programs'),('official-workshop-pages.json','programs'),
   ('official-exposition-rooms.json','rooms'),('official-original-legacy-sections.json','sections'),
   ('official-museum-crosslink-pages.json','pages'),('official-deep-museum-pages.json','pages')]
  urls=[x['source_url'] for name,key in names for x in json.loads((data/name).read_text())[key]]
  self.assertEqual(len(urls),467)
  self.assertEqual(len(set(urls)),467)
  self.assertEqual({urlsplit(x).netloc for x in urls},{'muzei-xleb.ru'})
  self.assertEqual({urlsplit(x).scheme for x in urls},{'https'})
  sitemap=(ROOT/'apps/web/src/app/sitemap.ts').read_text()
  self.assertIn('verifiedOriginalMuseumPaths()',sitemap)
  self.assertNotIn('publishedSitemapPaths(',sitemap)
  self.assertNotIn('"/",...verifiedOriginalMuseumPaths()',sitemap)

 def test_local_nginx_redirect_graph_has_no_self_loops_chains_missing_targets(self):
  result=preflight()
  self.assertEqual(result['rules'],881)
  self.assertEqual(result['page_rules'],368)
  self.assertEqual(result['image_rules'],513)
  self.assertEqual(result['missing_targets_or_loops_or_chains'],0)
  self.assertIn('NO-GO',result['production_status'])

if __name__=='__main__':unittest.main()
