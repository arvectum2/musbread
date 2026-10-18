"""Offline tests: no private museum originals necessary in CI."""
from __future__ import annotations
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from scripts import audit_official_pdf_accessibility as audit


class OfficialPdfA11yPreflightTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.original=b"%PDF-1.7\n" + b"stand-in bytes - no actual private museum contents"
        self.path=self.root/"original.pdf"
        self.path.write_bytes(self.original)
        self.item={
          "source":"/oficialnye-dokumenty-muzeya",
          "label":"Официальный пример для QA",
          "url":"https://muzei-xleb.ru/sites/default/files/test.pdf",
          "sha256":sha256(self.original).hexdigest(),
          "local_name":self.path.name,
          "size_bytes":len(self.original),
        }

    def test_hash_integrity_blocks_changed_original_before_invoking_poppler(self):
        with patch.object(audit,"PRIVATE",self.root),patch.object(audit,"run") as tool:
            self.item["sha256"]="0"*64
            with self.assertRaisesRegex(RuntimeError,"SHA/size mismatch"):
                audit.inspect(self.item)
            tool.assert_not_called()

    def test_untagged_unsearchable_pdf_must_be_a_high_priority_risk(self):
        def fake_run(args:list[str],timeout:int=25):
            output=(b"Pages: 42\nTagged: no\n" if args[0]=="pdfinfo"
                    else b" \n\x0c")
            return subprocess.CompletedProcess(args,0,output,b"")
        with patch.object(audit,"PRIVATE",self.root),patch.object(audit,"run",side_effect=fake_run):
            r=audit.inspect(self.item)
        self.assertEqual((r["page_count"],r["pdf_tagged"],r["first_3_pages_text_chars"]),(42,"no",0))
        self.assertEqual(r["first_3_pages_meaningful_text"],"insufficient")
        self.assertIn("HIGH",r["risk"])

    def test_pdf_text_layer_does_not_make_untagged_pdf_accessible(self):
        def fake_run(args:list[str],timeout:int=25):
            output=(b"Pages: 9\nTagged: no\n" if args[0]=="pdfinfo"
                    else b"Official text for QA test. "*150)
            return subprocess.CompletedProcess(args,0,output,b"")
        with patch.object(audit,"PRIVATE",self.root),patch.object(audit,"run",side_effect=fake_run):
            r=audit.inspect(self.item)
        self.assertEqual(r["first_3_pages_meaningful_text"],"likely")
        self.assertEqual(r["pdf_tagged"],"no")
        self.assertIn("HIGH: untagged",r["risk"])

    def test_tagged_pdf_still_requires_semantic_review(self):
        def fake_run(args:list[str],timeout:int=25):
            output=(b"Pages: 3\nTagged: yes\n" if args[0]=="pdfinfo"
                    else b"Official QA text. "*200)
            return subprocess.CompletedProcess(args,0,output,b"")
        with patch.object(audit,"PRIVATE",self.root),patch.object(audit,"run",side_effect=fake_run):
            r=audit.inspect(self.item)
        self.assertIn("still unverified",r["risk"])
        self.assertEqual(r["pdf_tagged"],"yes")

    def test_short_spoofed_source_manifest_refused(self):
        with self.assertRaisesRegex(RuntimeError,"44"):
            audit.inventory({"source":"https://muzei-xleb.ru","files":[self.item]})
        with self.assertRaisesRegex(RuntimeError,"Unexpected source"):
            audit.inventory({"source":"https://example.org","files":[self.item]*44})

    def test_safe_report_generation_does_not_write_original_contents(self):
        row={
           "source_section":"/oficialnye-dokumenty-muzeya",
           "label":"Проверенный пример", "url":self.item["url"],
           "sha256":self.item["sha256"],"format":"pdf",
           "size_bytes":1000,"page_count":3,
           "pdf_tagged":"no","first_3_pages_text_chars":0,
           "first_3_pages_meaningful_text":"insufficient",
           "risk":"HIGH: untagged and little extractable text",
        }
        with patch.object(audit,"REPORT",self.root/"report.csv"),patch.object(
            audit,"REPORT_MD",self.root/"summary.md"):
            audit.publish([row])
            md=(self.root/"summary.md").read_text()
            csv=(self.root/"report.csv").read_text(encoding="utf-8-sig")
        self.assertIn("TZ-211",md)
        self.assertIn("не сертификация",md)
        self.assertIn("Проверенный пример",csv)
        self.assertNotIn("%PDF-1.7",md+csv)


if __name__=="__main__":
    unittest.main()
