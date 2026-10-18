"""Original museum historical news: not a made-up upcoming museum schedule."""
import hashlib,json,re,unittest
from pathlib import Path
from lxml import html

ROOT=Path(__file__).resolve().parents[1]

class MuseumArchiveSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=json.loads((ROOT/'apps/web/src/data/official-museum-news-archive.json').read_text())
        cls.latest=json.loads((ROOT/'apps/web/src/data/official-museum-news.json').read_text())

    def test_forty_original_articles_have_exact_source_index_association(self):
        data=self.data
        self.assertEqual(data['source'],'https://muzei-xleb.ru')
        self.assertEqual(data['count'],40)
        self.assertEqual(len(data['indices']),4)
        urls=[]
        for n,index in enumerate(data['indices'],start=1):
            self.assertEqual(index['url'],f'https://muzei-xleb.ru/novosty?page={n}')
            self.assertEqual(len(index['article_paths']),10)
            self.assertEqual(len(set(index['article_paths'])),10)
            urls.extend(index['article_paths'])
        self.assertEqual(urls,[a['path'] for a in data['articles']])
        self.assertEqual(len(set(urls)),40)
        self.assertFalse({a['slug'] for a in data['articles']}
                         & {a['slug'] for a in self.latest['articles']})

    def test_short_real_news_are_preserved_and_never_represented_as_future_events(self):
        for article in self.data['articles']:
            with self.subTest(slug=article['slug']):
                self.assertTrue(re.fullmatch(r'/novosty/20\d{2}-\d\d-\d\d/[a-z0-9-]+',article['path']))
                self.assertEqual(article['source_url'],'https://muzei-xleb.ru'+article['path'])
                self.assertEqual(article['published_on'],article['path'].split('/')[2])
                self.assertEqual(article['slug'],'museum-news-'+article['published_on']+'-'+article['path'].split('/')[-1])
                self.assertEqual(hashlib.sha256(article['html'].encode()).hexdigest(),article['html_sha256'])
                text=' '.join(html.fromstring('<div>'+article['html']+'</div>').text_content().split())
                self.assertEqual(article['intro'],text[:245])
                if article.get('image_only'):
                    self.assertEqual(article['html'],'')
                    self.assertEqual(article['text_length'],0)
                    self.assertGreaterEqual(len(article['image_links']),1)
                    self.assertRegex(article['source_page_sha256'],r'^[a-f0-9]{64}$')
                    self.assertTrue(all(x['url'].startswith('https://muzei-xleb.ru/sites/default/files/') for x in article['image_links']))
                else:
                    self.assertGreaterEqual(article['text_length'],8)
                self.assertFalse(article['photos_rights_confirmed'])
                self.assertNotIn('<img',article['html'].lower())
                self.assertNotIn('<script',article['html'].lower())
                self.assertIn(article['archive_index_page'],(1,2,3,4))

if __name__=='__main__':unittest.main()
