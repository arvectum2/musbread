"""Offline 29-page signed contract/annex contract source map integrity."""
from __future__ import annotations
import copy
import importlib.util
import json
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
loader=importlib.util.spec_from_file_location("signed_musbread",ROOT/"scripts/audit_signed_contract.py")
signed=importlib.util.module_from_spec(loader)
loader.loader.exec_module(signed)

class SignedContractSpecTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=json.loads(signed.MAP.read_text(encoding="utf-8"))

    def test_pinned_source_and_29_pages(self):
        self.assertEqual(signed.digest(signed.MAP.read_bytes()),signed.REVIEWED_MAP_SHA)
        signed.validate(self.data,None)
        self.assertEqual(len(self.data["all_lines"]),1522)
        self.assertEqual(self.data["pages"],29)
        self.assertEqual(len(self.data["contract_clauses"]),124)
        self.assertEqual(self.data["pdf_sha256"],signed.PDF_SHA)

    def test_all_325_tz_atoms_align_to_signed_pdf(self):
        self.assertEqual(len(self.data["tz_atoms"]),325)
        self.assertTrue(all(x["signed_alignment_found"] for x in self.data["tz_atoms"]))
        manual={x["tz_id"]:x["signed_pdf_positions"] for x in self.data["tz_atoms"] if x["alignment_method"]=="human_verified_table_reflow"}
        self.assertEqual(set(manual),{"TZ-148","TZ-149","TZ-150"})
        self.assertEqual(manual["TZ-148"],[[19,46]])
        self.assertEqual(manual["TZ-149"],[[19,51]])
        self.assertEqual(manual["TZ-150"],[[20,4]])

    def test_contract_clause_and_annex_ranges(self):
        clauses={x["clause"] for x in self.data["contract_clauses"]}
        for k in ("1.2","1.4","2.4.6","2.4.15","3.1","3.5","5.1","5.4","5.8","5.11","6.1","12.1","12.2"):
            self.assertIn(k,clauses)
        self.assertEqual({x["scope"] for x in self.data["all_lines"]},
                         {"contract","ooz","rights_form","price","signatures"})
        self.assertEqual(self.data["signed_pages"]["price_annex"],"28")

    def test_report_price_and_deadlines_are_explicit(self):
        md=signed.REPORT.read_text(encoding="utf-8")
        self.assertIn("07.12.2026",md)
        self.assertIn("24 050,52",md)
        self.assertIn("14 949,48",md)
        self.assertIn("39 000,00",md)
        self.assertIn("трёх рабочих дней",md)
        self.assertNotIn("подписи криптографически проверены",md)

    def test_tampering_fails(self):
        for mutation in [
            lambda x:x["all_lines"].pop(),
            lambda x:x["all_lines"][1].update(page=30),
            lambda x:x["all_lines"][1].update(sha256="garbage"),
            lambda x:x["contract_clauses"].clear(),
            lambda x:x["tz_atoms"][0].update(tz_id="TZ-000"),
            lambda x:x["tz_atoms"][0].update(signed_pdf_positions=[]),
            lambda x:x.update(pdf_sha256="a"*64),
        ]:
            with self.subTest(mutation=str(mutation)):
                sample=copy.deepcopy(self.data)
                mutation(sample)
                with self.assertRaises((ValueError,KeyError)):
                    signed.validate(sample,None)

if __name__=="__main__":
    unittest.main()
