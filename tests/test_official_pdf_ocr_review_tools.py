import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SCRIPT=ROOT/'scripts/prepare_official_pdf_ocr_review.py'

class OfficialPdfOcrReviewToolTests(unittest.TestCase):
    def load(self):
        spec=importlib.util.spec_from_file_location('official_ocr',SCRIPT)
        module=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_private_review_transcript_escapes_untrusted_ocr_and_marks_unapproved(self):
        module=self.load()
        with tempfile.TemporaryDirectory() as dir:
            module.OUT=Path(dir)
            sha='a'*64
            folder=module.OUT/sha
            folder.mkdir()
            (folder/'001.txt').write_text('Первая страница <script>alert(1)</script>\n')
            (folder/'002.txt').write_text('Другая страница & суммы 20 000 рублей.\n')
            meta=module.make_review(sha, {
                'label':'Официальный документ <script>',
                'url':'https://muzei-xleb.ru/sites/default/files/test.pdf',
                'size_bytes':999,
            },2)
            body=(folder/'draft-accessible-transcript.html').read_text()
            self.assertNotIn('<script>',body)
            self.assertIn('&lt;script&gt;',body)
            self.assertIn('НЕ УТВЕРЖДЕНО',body)
            self.assertIn('Автоматическое распознавание',body)
            self.assertIn('Страница 1',body)
            self.assertIn('Страница 2',body)
            self.assertEqual(meta['pages'],2)
            self.assertIn('NOT ACCESSIBILITY APPROVED',meta['status'])
            self.assertEqual(meta['blank_or_short_pages'],[])

    def test_short_pages_explicitly_flagged_not_misrepresented_as_complete(self):
        module=self.load()
        with tempfile.TemporaryDirectory() as dir:
            module.OUT=Path(dir)
            sha='b'*64
            folder=module.OUT/sha
            folder.mkdir()
            (folder/'001.txt').write_text('а\n')
            (folder/'002.txt').write_text('Реальное длинное описание исходного документа для проверки.\n')
            info={'label':'Скан','url':'https://muzei-xleb.ru/scan.pdf','size_bytes':20}
            meta=module.make_review(sha,info,2)
            self.assertEqual(meta['blank_or_short_pages'],[1])
            self.assertEqual(json.loads((folder/'review-manifest.json').read_text())['pages'],2)
