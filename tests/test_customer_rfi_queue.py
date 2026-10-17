import csv,importlib.util,unittest
from datetime import date
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('rfi_sla',ROOT/'scripts/check_museum_response_sla.py')
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
class TestCustomerRFI(unittest.TestCase):
 def test_business_days(self):
  self.assertEqual(mod.due('2026-10-16'),date(2026,10,20))
  self.assertEqual(mod.due('2026-10-17'),date(2026,10,20))
  self.assertEqual(mod.due('2026-10-16',{date(2026,10,19)}),date(2026,10,21))
  self.assertEqual(mod.due('2026-10-19'),date(2026,10,21))
 def test_current_questions_are_complete_and_unsent(self):
  with (ROOT/'docs/tz-audit/requirements.psv').open(encoding='utf-8') as f:
   sources=list(csv.DictReader(f,delimiter='^'))
  with (ROOT/'docs/tz-audit/CUSTOMER_RFI_QUEUE.csv').open(encoding='utf-8-sig') as f:
   records=list(csv.DictReader(f,delimiter=';'))
  self.assertEqual(len(sources),325)
  self.assertEqual({r['tz'] for r in records},{r['ID'] for r in sources if r['Фактически готово']!='Да'})
  self.assertEqual(len(set(r['tz'] for r in records)),len(records))
  self.assertTrue(all(r['question'].endswith('?') for r in records))
  self.assertTrue(all(r['group'] and r['priority'] in ('P0','P1','P2') for r in records))
 def test_statuses_of_received_and_unanswered(self):
  import tempfile
  with tempfile.TemporaryDirectory() as folder:
   p=Path(folder)/'rfi.csv';p.write_text('rfi_id;received_date;response_date\nA;;\nB;2026-10-16;\nC;2026-10-16;2026-10-22\n')
   self.assertEqual([r[1] for r in mod.inspect(p,set(),date(2026,10,21))],['NOT_SENT','OVERDUE','ANSWERED_LATE'])
if __name__=='__main__':unittest.main()
