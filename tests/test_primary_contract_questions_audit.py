"""Audit prevents losing a source line, contract clause or question after updates."""
from collections import Counter
import csv
import importlib.util
from pathlib import Path
import subprocess
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"docs/tz-audit"
SOURCE=Path("/Volumes/ArvectumSSD/Arvectum/data/tenders/eis/0372200172326000015")

def rows(name,sep=";"):
 with (OUT/name).open(encoding="utf-8-sig",newline="") as f:
  return list(csv.DictReader(f,delimiter=sep))

class TestPrimaryContractQuestionAudit(unittest.TestCase):
 def test_every_open_requirement_has_a_distinct_short_question_and_source(self):
  src=rows("requirements.psv","^")
  q=rows("OPEN_CUSTOMER_QUESTIONS.csv")
  by_id={x["ID"]:x for x in src}
  expected={x["ID"] for x in src if x["Фактически готово"]!="Да"}
  self.assertEqual(len(src),325)
  self.assertEqual(len(q),284)
  self.assertEqual({x["ID"] for x in q},expected)
  self.assertEqual(len(set(x["Вопрос заказчику"] for x in q)),284)
  for item in q:
   self.assertEqual(item["Строки оригинала"],by_id[item["ID"]]["Строки tz.txt"])
   self.assertEqual(item["Учли в плане"],by_id[item["ID"]]["Учли в плане"])
   self.assertEqual(item["Готовность"],by_id[item["ID"]]["Фактически готово"])
   self.assertTrue(item["Вопрос заказчику"].endswith("?"))
   self.assertLessEqual(len(item["Вопрос заказчику"]),165)
   self.assertTrue(item["Что не выполнено"])
   self.assertTrue(item["Блокер/данные музея"])
  self.assertEqual(Counter(x["Учли в плане"] for x in q),Counter({"Да":165,"Частично":92,"Нет":27}))
  self.assertEqual(sum(x["Приоритет"]=="P0" for x in q),160)

 def test_contract_map_and_discrepancies_are_complete_and_grounded(self):
  c=rows("CONTRACT_CLAUSE_MAP.csv")
  risks=rows("CONTRACT_DISCREPANCIES_AND_RISKS.csv")
  self.assertEqual(len(c),125)
  self.assertEqual(len({x["Пункт договора"] for x in c}),125)
  self.assertIn("10",{x["Пункт договора"] for x in c})
  self.assertEqual(len(risks),25)
  self.assertEqual({x["ID"] for x in risks},{f"D{i:02d}" for i in range(1,26)})
  for r in risks:
   self.assertTrue(r["Строки источника"])
   self.assertTrue(r["Лаконичный вопрос заказчику"].endswith("?"))
  md=(OUT/"TZ_CONTRACT_ROADMAP_DEEP_AUDIT.md").read_text()
  for r in risks:self.assertIn(r["ID"],md)
  self.assertIn("317",md)
  self.assertIn("284",md)
  self.assertIn("27",md)

 def test_ready_count_unchanged_by_documentary_review(self):
  r=rows("requirements.psv","^")
  self.assertEqual(Counter(x["Фактически готово"] for x in r),Counter({"Да":41,"Частично":107,"Нет":177}))
  self.assertEqual(Counter(x["Учли в плане"] for x in r),Counter({"Да":205,"Частично":92,"Нет":28}))
  roadmap=(ROOT/"docs/ROADMAP.md").read_text()
  self.assertIn("Аудит дорожной карты против ПОЛНОГО ТЗ и проекта контракта",roadmap)
  self.assertIn("OPEN_CUSTOMER_QUESTIONS.md",roadmap)
  self.assertIn("CONTRACT_CLAUSE_MAP.md",roadmap)

 def test_question_generator_and_summary_are_idempotent(self):
  names=("OPEN_CUSTOMER_QUESTIONS.csv","OPEN_CUSTOMER_QUESTIONS.md",
         "TZ_CONTRACT_ROADMAP_DEEP_AUDIT.md","CONTRACT_CLAUSE_MAP.md")
  before={n:(OUT/n).read_bytes() for n in names}
  subprocess.run([sys.executable,str(ROOT/"scripts/build_customer_questions_audit.py")],cwd=ROOT,check=True,capture_output=True)
  subprocess.run([sys.executable,str(ROOT/"scripts/render_primary_audit_summary.py")],cwd=ROOT,check=True,capture_output=True)
  self.assertEqual({n:(OUT/n).read_bytes() for n in names},before)

 @unittest.skipUnless(SOURCE.is_dir(),"EIS originals only on user's Mac mini")
 def test_originals_word_line_census_and_annex_identity(self):
  script=ROOT/"scripts/audit_primary_contract.py"
  spec=importlib.util.spec_from_file_location("primary_contract_audit",script)
  module=importlib.util.module_from_spec(spec)
  assert spec.loader is not None
  spec.loader.exec_module(module)
  checked=module.source_data(SOURCE)
  self.assertEqual((len(checked["tz"]),len(checked["contract"])),(485,837))
  a=[module.normalized(t) for t in checked["tz"][59:396] if len(module.normalized(t))>=8]
  b=[module.normalized(t) for t in checked["contract"][365:702] if len(module.normalized(t))>=8]
  self.assertEqual(len(a),317)
  self.assertEqual(a,b)
  local=ROOT/".local_archive/primary-source-audit"
  for file,n in (("tz_485_line_audit.csv",485),("contract_837_line_audit.csv",837)):
   with (local/file).open(encoding="utf-8-sig",newline="") as f:
    self.assertEqual(len(list(csv.DictReader(f,delimiter=";"))),n)

if __name__=="__main__":unittest.main()
