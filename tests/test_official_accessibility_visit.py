import ast, json, re, unittest
from pathlib import Path
from lxml import html

ROOT=Path(__file__).resolve().parents[1]

class OfficialAccessibilityVisitTests(unittest.TestCase):
    def test_facts_are_grounded_in_exact_live_source_text(self):
        content=json.loads((ROOT/'apps/web/src/data/official-page-snapshots.json').read_text())
        item=next(p for p in content['pages'] if p['path']=='/informaciya-dlya-mgn')
        text=' '.join(html.fromstring('<div>'+item['html']+'</div>').text_content().split())
        ts=(ROOT/'apps/web/src/data/official-accessibility-visit.ts').read_text()
        sections=re.findall(r'sourcePhrases:\s*\[(.*?)\]',ts,re.S)
        self.assertEqual(len(sections),7)
        for section in sections:
            for phrase in ast.literal_eval('['+section+']'):
                with self.subTest(phrase=phrase):
                    self.assertIn(' '.join(phrase.split()),text)

    def test_accessibility_info_does_not_claim_an_unverified_certificate(self):
        code=(ROOT/'apps/web/src/components/VisitAccessibilityGuide.tsx').read_text()
        self.assertIn('Это исходная',code)
        self.assertIn('condensed ? 3',code)
        self.assertNotIn('<img',code)
