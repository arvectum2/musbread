import hashlib,json,unittest
from collections import Counter
from pathlib import Path
from lxml import html as lx

ROOT=Path(__file__).resolve().parents[1]
class OfficialExcursionProgramsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog=json.loads((ROOT/'apps/web/src/data/official-excursion-pages.json').read_text())
        cls.data=json.loads((ROOT/'apps/web/src/data/official-excursion-programs.json').read_text())

    def test_seventeen_real_distinct_programs_match_the_original_index_links(self):
        self.assertEqual(self.data['source'],'https://muzei-xleb.ru')
        self.assertEqual(self.data['count'],17)
        counts=Counter(p['category_slug'] for p in self.data['programs'])
        self.assertEqual(counts,{'excursion-interactive':6,'excursion-thematic':9,'excursion-theatrical':2})
        for category,count in counts.items():
            old=next(p for p in self.catalog['pages'] if p['cms_slug']==category)
            links=[a.get('href') for a in lx.fromstring('<div>'+old['html']+'</div>').xpath('.//a[@href]')
                   if (a.get('href') or '').startswith('https://muzei-xleb.ru/ekskursii/')]
            new=[p['source_url'] for p in self.data['programs'] if p['category_slug']==category]
            self.assertEqual(set(links),set(new))
            self.assertEqual(len(set(new)),count)

    def test_every_original_program_description_is_verified_and_photo_rights_unconfirmed(self):
        records=self.data['programs']
        self.assertEqual(len({p['slug'] for p in records}),17)
        for p in records:
            with self.subTest(slug=p['slug']):
                self.assertEqual(p['source_url'],'https://muzei-xleb.ru'+p['path'])
                self.assertEqual(p['slug'],'museum-tour-'+p['path'].rsplit('/',1)[-1])
                self.assertEqual(hashlib.sha256(p['html'].encode()).hexdigest(),p['html_sha256'])
                expected=' '.join(lx.fromstring('<div>'+p['html']+'</div>').text_content().split())[:250]
                self.assertEqual(p['intro'],expected)
                self.assertGreater(p['text_length'],85)
                self.assertGreater(len(p['title']),5)
                self.assertIs(p['photos_rights_confirmed'],False)
                self.assertNotIn('<img',p['html'].lower())
                self.assertNotIn('<script',p['html'].lower())
