"""Atom must stay an explicit red browser subcheck until a legitimate direct test or customer decision."""
import csv
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
T=ROOT/'docs/tz-audit'
class AtomRemainsRedUntilAccepted(unittest.TestCase):
    def test_brand_level_matrix_marks_atom_red_and_real_gost_green(self):
        with (T/'TZ259_BROWSER_VENDOR_STATUS_20261019.csv').open(encoding='utf-8-sig',newline='') as f:
            data=list(csv.DictReader(f,delimiter=';'))
        self.assertEqual(len(data),8)
        self.assertEqual(len({r['Браузер'] for r in data}),8)
        atom=next(r for r in data if r['Браузер']=='Atom')
        gost=next(r for r in data if r['Браузер']=='Chromium-GOST')
        self.assertTrue(atom['Светофор проверки именно браузера'].startswith('🔴'))
        self.assertIn('прямых испытаний Atom НЕТ',atom['Фактическое основание'])
        self.assertTrue(gost['Светофор проверки именно браузера'].startswith('🟢'))
        self.assertIn('23 из 23',gost['Фактическое основание'])
    def test_tz259_is_partial_but_atom_not_silently_waived(self):
        with (T/'requirements.psv').open(encoding='utf-8',newline='') as f:
            req={r['ID']:r for r in csv.DictReader(f,delimiter='^')}
        self.assertEqual(req['TZ-112']['Фактически готово'],'Да')
        self.assertEqual(req['TZ-259']['Фактически готово'],'Частично')
        self.assertIn('Atom 🔴 НЕ ПРОВЕРЕН',req['TZ-259']['Осталось выполнить'])
        self.assertIn('не согласовано',req['TZ-259']['Нужно от заказчика'])
    def test_written_scope_does_not_claim_equivalence(self):
        md=(T/'TZ259_ATOM_RED_DECISION_20261019.md').read_text()
        self.assertIn('не логическое доказательство',md)
        self.assertIn('Прямое испытание в Atom исполнителем не проводилось',md)
        self.assertIn('достаточность испытаний сайта в актуальных Chromium-браузерах',md)
if __name__=='__main__':unittest.main()
