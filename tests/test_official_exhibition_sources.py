import hashlib,json,unittest
from pathlib import Path
from lxml import html
from collections import Counter
ROOT=Path(__file__).resolve().parents[1]
class OfficialExhibitionsEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.idx=json.loads((ROOT/'apps/web/src/data/official-exhibition-indexes.json').read_text())
        cls.details=json.loads((ROOT/'apps/web/src/data/official-exhibition-details.json').read_text())

    def test_five_public_sections_do_not_invent_official_future_exhibitions(self):
        self.assertEqual(self.idx['count'],4)
        self.assertEqual(self.idx['source'],'https://muzei-xleb.ru')
        self.assertEqual([p['slug'] for p in self.idx['indexes']],[
            'exhibitions-current','exhibitions-traveling','exhibitions-past','exhibitions-virtual'])
        self.assertEqual([len(p['linked_exhibitions']) for p in self.idx['indexes']],[2,4,12,12])
        for item in self.idx['indexes']:
            with self.subTest(index=item['slug']):
                self.assertEqual(hashlib.sha256(item['html'].encode()).hexdigest(),item['html_sha256'])
                self.assertIs(item['images_rights_confirmed'],False)
                self.assertEqual(len(item['linked_exhibitions']),len(set(x['source_url'] for x in item['linked_exhibitions'])))
                self.assertNotIn('<img',item['html'].lower())
                for e in item['linked_exhibitions']:
                    self.assertEqual(e['source_url'],'https://muzei-xleb.ru'+e['path'])
                    self.assertIn(e['source_url'],item['html'])

    def test_two_current_exhibition_ranges_are_exact_original_museum_ranges(self):
        current=self.idx['indexes'][0]
        self.assertEqual([x['date_text'] for x in current['linked_exhibitions']],[
            '3 октября – 7 декабря 2026 г.',
            '3 сентября - 23 ноября 2026 г.',
        ])
        text=' '.join(html.fromstring('<div>'+current['html']+'</div>').text_content().split())
        for e in current['linked_exhibitions']:
            self.assertIn(e['date_text'],text)

    def test_six_detail_pages_match_exact_category_links_and_source_digest(self):
        self.assertEqual(self.details['count'],6)
        seen=set()
        index={i['slug']:i for i in self.idx['indexes']}
        self.assertEqual(Counter(p['category_slug'] for p in self.details['exhibitions']),{
            'exhibitions-current':2,'exhibitions-traveling':4})
        for p in self.details['exhibitions']:
            with self.subTest(detail=p['slug']):
                self.assertNotIn(p['slug'],seen);seen.add(p['slug'])
                self.assertEqual(hashlib.sha256(p['html'].encode()).hexdigest(),p['html_sha256'])
                self.assertEqual(p['source_url'],'https://muzei-xleb.ru'+p['path'])
                self.assertIn(p['source_url'],[e['source_url'] for e in index[p['category_slug']]['linked_exhibitions']])
                self.assertIs(p['photos_rights_confirmed'],False)
                self.assertNotIn('<img',p['html'].lower())
                self.assertNotIn('<script',p['html'].lower())
                self.assertGreater(p['text_length'],100)

    def test_shop_and_workshops_source_does_not_mix_with_exhibition_archive(self):
        titles=[e['title'] for i in self.idx['indexes'] for e in i['linked_exhibitions']]
        self.assertIn('«Хлеб блокадного города»',titles)
        self.assertIn('«От ремесла до искусства. Резные пряничные доски»',titles)
        self.assertEqual(len(titles),30)
