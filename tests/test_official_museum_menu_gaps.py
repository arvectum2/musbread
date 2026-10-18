"""Verify preserved actual museum menu content; not invented articles."""
from __future__ import annotations
import json,hashlib,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class MenuGapsSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.src=json.loads((ROOT/'apps/web/src/data/official-museum-menu-gaps.json').read_text())
    def test_exact_retrieved_landing_articles(self):
        d=self.src
        self.assertEqual(d['source'],'https://muzei-xleb.ru')
        self.assertEqual(d['count'],6)
        pages={p['path']:p for p in d['pages']}
        for path in (
            '/uchetnaya-politika','/protivodeystvie-terrorizmu',
            '/antimonopolnyy-komplaens','/gostevaya-kniga',
            '/adres','/covid-19'):
            self.assertIn(path,pages)
            row=pages[path]
            self.assertEqual(row['source_url'],'https://muzei-xleb.ru'+path)
            self.assertEqual(hashlib.sha256(row['html'].encode()).hexdigest(),row['html_sha256'])
            self.assertNotIn('<script',row['html'].lower())
            self.assertNotIn('<iframe',row['html'].lower())
        self.assertEqual(len(pages['/uchetnaya-politika']['document_links']),7)
        self.assertEqual(len(pages['/protivodeystvie-terrorizmu']['document_links']),3)
        self.assertEqual(len(pages['/antimonopolnyy-komplaens']['document_links']),1)
        self.assertEqual({x['path'] for x in d['not_articles']},
                         {'/informaciya-dlya-dariteley','/dokumenty'})
    def test_private_guestbook_and_outdated_covid_not_publicly_migrated(self):
        code=(ROOT/'apps/web/src/data/official-page-snapshots.ts').read_text()
        self.assertIn('institutionPages',code)
        self.assertNotIn('  "/gostevaya-kniga",',code)
        self.assertNotIn('  "/covid-19",',code)
        self.assertIn('"/adres",',code)
        self.assertIn('"/uchetnaya-politika",',code)
    def test_no_rewriting_official_pdf(self):
        code=(ROOT/'scripts/cache_official_missing_menu_docs.py').read_text()
        self.assertIn("dst.write_bytes(buf)",code)
        self.assertNotIn('OCR',code.split('def main()')[1])
if __name__=='__main__':unittest.main()
