"""96 original PDFs can be viewed intact; do not assert screen reader conformance."""
import csv, json, sys, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from export_official_museum_original_documents import source_documents
CSV=ROOT/'docs/tz-audit/ORIGINAL_MUSEUM_PDF_OPENABILITY_HTTP_20261019.csv'
SUMMARY=ROOT/'docs/tz-audit/ORIGINAL_MUSEUM_PDF_OPENABILITY_HTTP_20261019.json'
class OriginalPdfViewerReportTests(unittest.TestCase):
 def test_all_96_source_pdfs_http_render_and_hash_match_without_ocr(self):
  docs={p:i for p,i in source_documents().items() if i['format']=='pdf'}
  with CSV.open(encoding='utf-8-sig',newline='') as f: rows=list(csv.DictReader(f,delimiter=';'))
  self.assertEqual(len(docs),96)
  self.assertEqual(len(rows),96)
  self.assertEqual({r['Путь на сайте'] for r in rows},set(docs))
  self.assertEqual(len({r['Путь на сайте'] for r in rows}),96)
  for row in rows:
   with self.subTest(path=row['Путь на сайте']):
    self.assertEqual(row['Результат'],'PASS')
    self.assertEqual(int(row['HTTP']),200)
    self.assertTrue(row['MIME'].startswith('application/pdf'))
    self.assertEqual(int(row['Байт']),docs[row['Путь на сайте']]['size_bytes'])
    self.assertGreater(int(row['Страниц']),0)
    self.assertEqual(row['SHA256 совпадает'],'да')
    self.assertEqual(row['Inline (не форсируется скачивание)'],'да')
    self.assertEqual(row['Отрисовка первой страницы'],'да')
    self.assertEqual(row['Ошибка'],'')
 def test_summary_is_precise_and_does_not_fake_assistive_technology_accessibility(self):
  d=json.loads(SUMMARY.read_text())
  self.assertEqual((d['checked_pdf'],d['passed'],d['failed']), (96,96,0))
  self.assertEqual(d['first_pages_rendered'],96)
  self.assertEqual(d['total_pages'],775)
  self.assertEqual(d['total_bytes'],296223133)
  self.assertTrue(d['no_pdf_modified'])
  self.assertTrue(d['no_ocr_performed'])
  self.assertIn('NOT a screen-reader',d['not_verified'])
if __name__=='__main__':unittest.main()
