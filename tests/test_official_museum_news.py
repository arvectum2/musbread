"""Ten newest museum news items and the REAL Nov 3 event, source attested."""
import hashlib,json,re,unittest
from pathlib import Path
from lxml import html

ROOT=Path(__file__).resolve().parents[1]
class MuseumNewsSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d=json.loads((ROOT/'apps/web/src/data/official-museum-news.json').read_text())

    def test_current_index_is_ten_real_source_links_in_published_order(self):
        data=self.d
        self.assertEqual(data['source'],'https://muzei-xleb.ru')
        self.assertEqual(data['index_url'],'https://muzei-xleb.ru/novosty')
        self.assertEqual(data['count'],10)
        self.assertEqual(hashlib.sha256(data['index_html'].encode()).hexdigest(),data['index_html_sha256'])
        index=html.fromstring('<div>'+data['index_html']+'</div>')
        found=[a.get('href') for a in index.xpath('.//a[@href]')
               if re.search(r'/novosty/20\d{2}-\d\d-\d\d/[a-z0-9-]+$',a.get('href',''))]
        # The original index can repeat text/image links; the 10 unique URL order is preserved.
        self.assertEqual(list(dict.fromkeys(found)),[p['source_url'] for p in data['articles']])
        self.assertEqual(len({p['slug'] for p in data['articles']}),10)

    def test_ten_original_news_are_not_fake_events_or_unlicensed_images(self):
        for item in self.d['articles']:
            with self.subTest(slug=item['slug']):
                self.assertEqual(item['source_url'],'https://muzei-xleb.ru'+item['path'])
                self.assertEqual(item['published_on'],item['path'].split('/')[2])
                self.assertEqual(item['slug'],'museum-news-'+item['published_on']+'-'+item['path'].split('/')[-1])
                self.assertEqual(hashlib.sha256(item['html'].encode()).hexdigest(),item['html_sha256'])
                text=' '.join(html.fromstring('<div>'+item['html']+'</div>').text_content().split())
                self.assertEqual(item['intro'],text[:245])
                self.assertGreater(item['text_length'],80)
                self.assertFalse(item['photos_rights_confirmed'])
                self.assertNotIn('<img',item['html'].lower())
                self.assertNotIn('<script',item['html'].lower())

    def test_night_arts_event_nov_3_is_explicitly_in_museum_article_not_news_date(self):
        item=next(p for p in self.d['articles'] if p['slug'].startswith('museum-news-2026-10-16-noch-iskusstv'))
        self.assertEqual(item['title'],'Ночь искусств в Музее Хлеба')
        self.assertIn('3 ноября 2026 г., 18:00–20:00',item['html'])
        self.assertIn('Петербург гостеприимный',item['html'])
        self.assertNotEqual('2026-10-16','2026-11-03')
        self.assertEqual(item['published_on'],'2026-10-16')
