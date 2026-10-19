"""Static migration of original museum URLs must be precise and loop-free."""
import csv,sys,unittest
from pathlib import Path
from urllib.parse import urlsplit
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from build_museum_legacy_page_aliases import build_map,build_aliases
class OriginalMuseumPageCompatibilityTests(unittest.TestCase):
    def test_source_routes_have_one_internal_dest_and_never_redirect_to_self(self):
        m=build_map()
        self.assertGreaterEqual(len(m),185)
        self.assertIn('/novosty',m)
        self.assertEqual(m['/novosty']['target'],'/news/')
        self.assertEqual(m['/istoriya-zdaniya']['target'],'/guide/building-history/')
        self.assertEqual(m['/ekspozicii']['target'],'/guide/museum-exposition/')
        self.assertEqual(m['/informaciya-dlya-mgn']['target'],'/guide/accessible-museum/')
        self.assertGreaterEqual(sum(item['why']=='original-news-article' for item in m.values()),90)
        for source,item in m.items():
            with self.subTest(source=source):
                target=item['target'];dest=urlsplit(target)
                self.assertTrue(source.startswith('/'))
                self.assertTrue(target.startswith('/'))
                self.assertEqual(dest.scheme,'')
                self.assertEqual(dest.netloc,'')
                self.assertNotEqual(source, dest.path.rstrip('/'))
                self.assertNotIn('https://muzei-xleb.ru',target)
    def test_all_alias_destinations_exist_in_current_static_site(self):
        # App build must have run before this check; next build also does this
        # automatically through package.json postbuild.
        p=ROOT/'apps/web/out'
        self.assertTrue(p.is_dir())
        result=build_aliases(write=False,strict=True)
        self.assertGreaterEqual(len(result['rows']),185)
        self.assertEqual(result['missing'],[])
        self.assertEqual(result['collisions'],[])
    def test_all_legacy_node_fallbacks_have_real_keyboard_landmarks(self):
        from lxml import html
        folder=ROOT/'apps/web/out/node'
        files=list(folder.glob('*/index.html'))
        self.assertEqual(len(files),88)
        for file in files:
            with self.subTest(path=file.parent.name):
                tree=html.fromstring(file.read_bytes())
                self.assertEqual(len(tree.xpath('//a[@href="#main"]')),1)
                self.assertEqual(len(tree.xpath('//main[@id="main"]')),1)
                self.assertEqual(len(tree.xpath('//h1')),1)
                self.assertEqual(len(tree.xpath('//meta[@name="viewport"]')),1)
                self.assertEqual(len(tree.xpath('//meta[@http-equiv="refresh"]')),1)

    def test_redirected_original_news_pages_resolve_to_verified_article_html(self):
        m=build_map()
        source=next(s for s,item in m.items() if item['why']=='original-news-article')
        new=ROOT/'apps/web/out'/m[source]['target'].lstrip('/')/'index.html'
        self.assertTrue(new.is_file())
        self.assertIn('data-official-original-news=',new.read_text())
