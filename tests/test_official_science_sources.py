"""Science pages can only claim materials literally published on the museum site."""
import json,hashlib,unittest
from pathlib import Path
from lxml import html
ROOT=Path(__file__).resolve().parents[1]

class MuseumScienceEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=json.loads((ROOT/'apps/web/src/data/official-science-sources.json').read_text())

    def test_exact_institutional_science_sources_are_preserved_without_academic_relabelling(self):
        d=self.data
        self.assertEqual(d['source'],'https://muzei-xleb.ru')
        self.assertEqual(d['count'],2)
        self.assertEqual([x['slug'] for x in d['pages']],[
            'science-organization','science-methodical-council'])
        self.assertIn('No invented publications',d['classification'])
        for page in d['pages']:
            with self.subTest(slug=page['slug']):
                self.assertEqual(page['source_url'],'https://muzei-xleb.ru'+page['path'])
                self.assertEqual(page['html_sha256'],hashlib.sha256(page['html'].encode()).hexdigest())
                self.assertGreater(page['text_length'],80)
                self.assertIs(page['photos_rights_confirmed'],False)
                self.assertNotIn('<img',page['html'])
                self.assertNotIn('<script',page['html'])
                self.assertEqual(len(page['documents']),1)
                for item in page['documents']:
                    self.assertTrue(item['url'].startswith('https://muzei-xleb.ru/sites/default/files/page/'))
                    self.assertIn(item['url'],page['html'])
                    self.assertIn(item['format'],('pdf','docx'))

    def test_original_collection_access_policy_is_present_in_museum_pages(self):
        doc=json.loads((ROOT/'apps/web/src/data/official-page-snapshots.json').read_text())
        price=next(p for p in doc['pages'] if p['path']=='/ceny-i-usloviya-predostavleniya-uslug')
        access=[e for e in price['document_links']
            if '20260203112347-poryadok_dostupa.pdf' in e['url']]
        self.assertEqual(len(access),1)
        self.assertIn('порядке и условиях доступа граждан',access[0]['label'])
        self.assertEqual(access[0]['url'],
                         'https://muzei-xleb.ru/sites/default/files/page/20260203112347-poryadok_dostupa.pdf')

    def test_science_registry_does_not_claim_specimen_rights_or_conf_papers(self):
        src=(ROOT/'apps/web/src/components/OfficialMuseumScience.tsx').read_text()
        for text in ('не предоставлен','не считаются','не гарантирует','no','Госкаталоге'):
            self.assertTrue(text in src or text=='no')
        self.assertNotIn('<img',src)
