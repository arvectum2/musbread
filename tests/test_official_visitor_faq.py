import hashlib,json,unittest
from pathlib import Path
from lxml import html

ROOT=Path(__file__).resolve().parents[1]
class MuseumFAQSourceEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        main=json.loads((ROOT/'apps/web/src/data/official-page-snapshots.json').read_text())
        extra=json.loads((ROOT/'apps/web/src/data/official-visitor-guidance.json').read_text())
        cls.sources={r['path']:r for r in main['pages']+extra['pages']}
        cls.guidance=extra
        cls.faq=json.loads((ROOT/'apps/web/src/data/official-visitor-faq.json').read_text())

    def test_nine_distinct_faq_answers_use_real_museum_sources(self):
        self.assertEqual(self.faq['count'],9)
        self.assertEqual(len(self.faq['questions']),9)
        self.assertEqual(len({q['id'] for q in self.faq['questions']}),9)
        for q in self.faq['questions']:
            with self.subTest(question=q['id']):
                p=self.sources[q['source_path']]
                self.assertEqual(p['source_url'],q['source_url'])
                self.assertEqual(hashlib.sha256(p['html'].encode()).hexdigest(),q['source_html_sha256'])
                normalized=' '.join(html.fromstring('<div>'+p['html']+'</div>').text_content().split())
                for evidence in q['source_phrases']:
                    self.assertIn(' '.join(evidence.split()),normalized)
                self.assertGreater(len(q['answer']),40)
                self.assertNotIn('<',q['answer'])

    def test_excursion_conditions_and_scanned_original_have_separate_scopes(self):
        self.assertEqual(self.guidance['count'],2)
        excursion=self.sources['/ekskursii']
        self.assertEqual(len(excursion['document_links']),1)
        link=excursion['document_links'][0]
        self.assertIn('organizovannymi_gruppami_ekskursiy.pdf',link['url'])
        self.assertIn('https://muzei-xleb.ru',link['url'])
        self.assertNotIn('covid',str(self.faq).lower())
        self.assertNotIn('маски обязательны',str(self.faq).lower())

    def test_visitor_faq_and_planning_components_show_official_links(self):
        faq=(ROOT/'apps/web/src/components/OfficialVisitorFAQ.tsx').read_text()
        guide=(ROOT/'apps/web/src/components/OfficialVisitorRules.tsx').read_text()
        self.assertIn('<details',faq)
        self.assertIn('item.source_url',faq)
        self.assertIn('officialExcursionGuidance.source_url',guide)
        self.assertIn('относятся к экскурсионному посещению',guide)
        self.assertIn('organized.url',guide)
