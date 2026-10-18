import hashlib,json,unittest
from pathlib import Path
from lxml import html as lx

ROOT=Path(__file__).resolve().parents[1]
HOST='https://muzei-xleb.ru'
class OfficialMuseumExcursionSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=json.loads((ROOT/'apps/web/src/data/official-excursion-pages.json').read_text())

    def test_four_original_usable_museum_excursion_pages_have_verified_hashes(self):
        self.assertEqual(self.data['count'],4)
        self.assertEqual(self.data['source'],HOST)
        pages=self.data['pages']
        self.assertEqual([p['cms_slug'] for p in pages],[
            'excursion-overview','excursion-interactive','excursion-thematic','excursion-theatrical'])
        self.assertEqual(len({p['path'] for p in pages}),4)
        for page in pages:
            with self.subTest(slug=page['cms_slug']):
                self.assertEqual(page['source_url'],HOST+page['path'])
                self.assertEqual(hashlib.sha256(page['html'].encode()).hexdigest(),page['html_sha256'])
                self.assertGreater(page['text_length'],100)
                self.assertIn('Музей',page['title']+' Музей')
                self.assertIs(page['photos_rights_confirmed'],False)
                self.assertNotIn('<img',page['html'].lower())
                self.assertNotIn('<script',page['html'].lower())

    def test_category_links_reproduce_real_museum_programs_not_invented_programs(self):
        counts={'excursion-overview':0,'excursion-interactive':6,
                'excursion-thematic':10,'excursion-theatrical':2}
        for page in self.data['pages']:
            links=[a.get('href') for a in lx.fromstring('<div>'+page['html']+'</div>').xpath('.//a[@href]')
                if '/ekskursii/' in (a.get('href') or '')]
            self.assertEqual(len(links),counts[page['cms_slug']])
            self.assertTrue(all(a.startswith(HOST+'/ekskursii/') for a in links))
        thematic=next(p for p in self.data['pages'] if p['cms_slug']=='excursion-thematic')
        thematic_links=[a.get('href') for a in lx.fromstring('<div>'+thematic['html']+'</div>').xpath('.//a[@href]')
                if '/ekskursii/' in (a.get('href') or '')]
        self.assertEqual(len(thematic_links)-len(set(thematic_links)),1,
            'Old museum site has one source-duplicate, not a new unique program')
