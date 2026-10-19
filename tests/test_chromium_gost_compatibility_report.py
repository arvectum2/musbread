"""Check genuine browser evidence without substituting generic Chromium for GOST."""
import json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
REPORT=ROOT/'docs/tz-audit/CHROMIUM_GOST_BROWSER_CHECK_20261019.json'
class ChromiumGostAcceptanceEvidence(unittest.TestCase):
 def test_actual_real_gost_browser_and_corpus_all_pass(self):
  report=json.loads(REPORT.read_text(encoding='utf-8'))
  self.assertEqual(report['browser'],'Chromium-Gost')
  self.assertEqual(report['version'],'152.0.7977.149')
  self.assertEqual(report['native_arch'],'macos-arm64')
  self.assertTrue(report['isolated_local_http'])
  self.assertEqual((report['checks'],report['passed'],report['failed']),(23,23,0))
  rows=report['results']
  self.assertEqual(len(rows),23)
  self.assertTrue(all(row['status']=='PASS' for row in rows))
  actual=next(row for row in rows if row['test']=='actual Chromium GOST UA')
  self.assertIn('Chromium GOST',actual['detail'])
  sweep=next(row for row in rows if row['test']=='all original site HTML pages in actual Chromium-GOST')
  self.assertIn('"checked":467',sweep['detail'])
  self.assertIn('"failed":[]',sweep['detail'])
 def test_matrix_does_not_falsely_pass_atom_or_all_browser_brands(self):
  import csv
  with (ROOT/'docs/tz-audit/requirements.psv').open(encoding='utf-8') as f:
   req={r['ID']:r for r in csv.DictReader(f,delimiter='^')}
  self.assertEqual(req['TZ-112']['Фактически готово'],'Да')
  self.assertEqual(req['TZ-111']['Фактически готово'],'Частично')
  self.assertEqual(req['TZ-259']['Фактически готово'],'Частично')
  self.assertIn('Atom',req['TZ-259']['Осталось выполнить'])
if __name__=='__main__':unittest.main()
