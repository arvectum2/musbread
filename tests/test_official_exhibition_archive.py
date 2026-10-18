"""Private museum past & virtual exhibition texts from two original catalogues."""
import hashlib,json,unittest,re
from pathlib import Path
from lxml import html
ROOT=Path(__file__).resolve().parents[1]
class MuseumPastExhibitionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.s=json.loads((ROOT/'apps/web/src/data/official-exhibition-archive.json').read_text())
        cls.idx=json.loads((ROOT/'apps/web/src/data/official-exhibition-indexes.json').read_text())
    def test_past_virtual_link_exact_original_catalogue_and_unique(self):
        self.assertEqual(self.s['source'],'https://muzei-xleb.ru')
        self.assertEqual(self.s['expected'],24)
        self.assertEqual(self.s['count'],24)
        self.assertEqual(self.s['errors'],[])
        original={r['source_url']:(x['slug'],r['title']) for x in self.idx['indexes']
                  if x['slug'] in ('exhibitions-past','exhibitions-virtual')
                  for r in x['linked_exhibitions']}
        self.assertEqual(len(original),24)
        self.assertEqual(set(original),{p['source_url'] for p in self.s['exhibitions']})
        self.assertEqual(len({p['slug'] for p in self.s['exhibitions']}),24)
        for p in self.s['exhibitions']:
            self.assertEqual((p['category_slug'],p['index_label']),original[p['source_url']])
    def test_original_text_exact_hash_and_no_unlicensed_images(self):
        for p in self.s['exhibitions']:
            with self.subTest(slug=p['slug']):
                self.assertTrue(re.fullmatch(r'/vistavky/20\d{2}-\d\d-\d\d/[a-z0-9-]+',p['path']))
                self.assertEqual(p['source_url'],'https://muzei-xleb.ru'+p['path'])
                self.assertEqual(p['html_sha256'],hashlib.sha256(p['html'].encode()).hexdigest())
                self.assertEqual(p['intro'],' '.join(html.fromstring('<div>'+p['html']+'</div>').text_content().split())[:245])
                self.assertFalse(p['photos_rights_confirmed'])
                self.assertNotIn('<img',p['html'].lower())
                self.assertNotIn('<script',p['html'].lower())
                if p.get('image_only'):
                    self.assertEqual(p['html'],'')
                    self.assertTrue(p['image_links'])
                else:self.assertGreaterEqual(p['text_length'],8)
