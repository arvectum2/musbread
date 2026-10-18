"""Only exhibition pages linked by genuine museum news may be imported."""
import hashlib,json,re,unittest
from pathlib import Path
from lxml import html
ROOT=Path(__file__).resolve().parents[1]
class MuseumNewsExhibitionProofTests(unittest.TestCase):
    def test_exact_two_original_exhibition_articles_are_linked_from_source_news(self):
        d=json.loads((ROOT/'apps/web/src/data/official-exhibition-news-linked.json').read_text())
        n=json.loads((ROOT/'apps/web/src/data/official-museum-news-archive.json').read_text())
        self.assertEqual(d['source'],'https://muzei-xleb.ru')
        self.assertEqual(d['count'],2)
        self.assertEqual(len(d['exhibitions']),2)
        source={a['slug']:a for a in n['articles']}
        for exhibit in d['exhibitions']:
            with self.subTest(exhibit=exhibit['slug']):
                self.assertRegex(exhibit['path'],r'^/vistavky/20\d{2}-\d\d-\d\d/[a-z0-9-]+$')
                self.assertEqual(exhibit['source_url'],'https://muzei-xleb.ru'+exhibit['path'])
                self.assertEqual(exhibit['category_slug'],'exhibitions-past')
                self.assertGreater(exhibit['text_length'],100)
                self.assertEqual(exhibit['html_sha256'],hashlib.sha256(exhibit['html'].encode()).hexdigest())
                self.assertEqual(exhibit['image_links'],[])
                news=source[exhibit['linked_news_slug']]
                self.assertEqual(exhibit['linked_news_html_sha256'],news['html_sha256'])
                self.assertEqual(exhibit['linked_news_url'],news['source_url'])
                self.assertEqual([a.get('href') for a in html.fragment_fromstring(news['html'],create_parent='div').xpath('.//a[@href]')].count(exhibit['source_url']),1)
                self.assertFalse(exhibit['photos_rights_confirmed'])
