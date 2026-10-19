"""Owner decision register cannot silently lose or reclassify any red clause."""
import csv
import subprocess
import sys
import unittest
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
P=ROOT/'docs/tz-audit'
class RedOwnerTriageTest(unittest.TestCase):
 def test_all_126_current_red_clauses_grouped_exactly_once(self):
  with (P/'TZ_EXECUTION_MATRIX.csv').open(encoding='utf-8-sig',newline='') as f:
   original=list(csv.DictReader(f,delimiter=';'))
  with (P/'RED_126_OWNER_DECISION_TRIAGE_20261019.csv').open(encoding='utf-8-sig',newline='') as f:
   triage=list(csv.DictReader(f,delimiter=';'))
  self.assertEqual(len(original),325)
  self.assertEqual(Counter(x['Готовность'] for x in original),{'Да':84,'Частично':115,'Нет':126})
  self.assertEqual(len(triage),126)
  reds={r['ID ТЗ']:r for r in original if r['Готовность']=='Нет'}
  self.assertEqual(set(x['ID'] for x in triage),set(reds))
  self.assertEqual(len({x['ID'] for x in triage}),len(triage))
  self.assertEqual(Counter(x['Вид зависимости'] for x in triage),{
   'Дизайн на паузе':72,
   'После договора: серверы, эксплуатация, акты':37,
   'Правовые нормы и официальная проверка':10,
   'Не хватает выбора процесса музеем':3,
   'Технически можно продвигать до договора':4,
  })
  for row in triage:
   official=reds[row['ID']]
   self.assertEqual(row['Название требования'],official['Требование'])
   self.assertEqual(row['Что реально ещё сделать'],official['Что сделать для завершения'])
   self.assertTrue(row['Подход без нарушения ТЗ'])
 def test_markdown_has_exactly_one_row_for_each_current_red(self):
  md=(P/'RED_126_OWNER_DECISION_TRIAGE_20261019.md').read_text()
  with (P/'TZ_EXECUTION_MATRIX.csv').open(encoding='utf-8-sig',newline='') as f:
   reds=[r['ID ТЗ'] for r in csv.DictReader(f,delimiter=';') if r['Готовность']=='Нет']
  detail=md.split('## Построчный реестр всех 126 красных пунктов',1)[1]
  for ident in reds:self.assertEqual(detail.count('| '+ident+' |'),1,ident)
  self.assertIn('без нового дизайна',md)
  self.assertIn('после договора',md.lower())
 def test_generator_deterministic(self):
  paths=[P/'RED_126_OWNER_DECISION_TRIAGE_20261019.csv',P/'RED_126_OWNER_DECISION_TRIAGE_20261019.md']
  before=[p.read_bytes() for p in paths]
  subprocess.run([sys.executable,str(ROOT/'scripts/build_red_tz_decision_triage.py')],cwd=ROOT,capture_output=True,check=True)
  self.assertEqual(before,[p.read_bytes() for p in paths])
if __name__=='__main__':unittest.main()
