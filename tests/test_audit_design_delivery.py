import csv
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

from scripts.audit_design_delivery import (
    ROOT, define, check_design_catalog, tender_requirements, inventory,
    as_markdown, request_markdown, plausible_format, require_matching_report,
)

class DesignDeliveryAuditTests(unittest.TestCase):
    def test_registry_has_all_explicit_tz_carrier_variants_and_original_references(self):
        rows = define()
        check_design_catalog(rows, tender_requirements(ROOT))
        self.assertGreaterEqual(len(rows), 110)
        self.assertEqual(sum(x.id.startswith("POSTER-") for x in rows), 11)
        self.assertEqual(sum(x.id.startswith("PPT-") for x in rows), 16)
        self.assertEqual(sum(x.id.startswith("VK-RUBRIC-") for x in rows), 4)
        self.assertEqual(sum(x.id.startswith("MERCH-") for x in rows), 9)
        for name in ("SOURCE-AI", "SOURCE-EPS", "SOURCE-SVG", "SOURCE-PSD", "SOURCE-TIFF",
                     "SOURCE-PPT", "SOURCE-PPTX", "DISK-HDD","DISK-CLOUD",
                     "DOC-PAPER","ACT-RIGHTS","CONCEPT-EMAIL","CONCEPT-DEMO"):
            self.assertIn(name,{r.id for r in rows})
        for r in rows:
            self.assertTrue(all(tz in tender_requirements(ROOT) for tz in r.tz.split(",")))

    def test_real_repo_does_not_claim_demos_as_approved_design_assets(self):
        rows, stats = inventory(ROOT)
        self.assertEqual(stats["customer_approved"],0)
        self.assertEqual(stats["missing"],stats["targets"])
        self.assertFalse(stats["rights_transferred"])
        self.assertIn("not approved",as_markdown(rows,stats).lower())
        self.assertIn("not sent",request_markdown(rows,tender_requirements(ROOT)).lower())

    def test_magic_checks_catch_disguised_assets_and_non_pptx_zip(self):
        with tempfile.TemporaryDirectory() as temporary:
            file = Path(temporary)/"fake.pdf"
            file.write_bytes(b"<html>fake PDF</html>")
            self.assertFalse(plausible_format(file, ".pdf")[0])
            file.write_bytes(b"%PDF-1.7\nsynthetic nonempty\n")
            self.assertTrue(plausible_format(file, ".pdf")[0])
            file = Path(temporary)/"fake.svg"
            file.write_text("<html>wrong root</html>")
            self.assertFalse(plausible_format(file, ".svg")[0])
            file.write_text('<svg xmlns="http://www.w3.org/2000/svg"/>')
            self.assertTrue(plausible_format(file, ".svg")[0])
            file = Path(temporary)/"presentation.pptx"
            with ZipFile(file,"w") as output:
                output.writestr("random.txt","not a PowerPoint")
            self.assertFalse(plausible_format(file, ".pptx")[0])
            with ZipFile(file,"w") as output:
                output.writestr("[Content_Types].xml",'<Types/>')
                output.writestr("ppt/presentation.xml",'<presentation/>')
            self.assertTrue(plausible_format(file, ".pptx")[0])

    def test_evidence_only_in_repo_docs_never_is_customer_approved(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            (root/"docs/tz-audit").mkdir(parents=True)
            (root/"docs/handoff").mkdir()
            (root/"docs/design").mkdir()
            (root/"docs/tz-audit/requirements.psv").write_bytes(
                (ROOT/"docs/tz-audit/requirements.psv").read_bytes())
            (root/"docs/design/image.png").write_bytes(
                b"\x89PNG\r\n\x1a\n"+b"synthetic PNG fixture")
            (root/"docs/handoff/DESIGN_EVIDENCE.csv").write_text(
                "id,path,museum_approval,notes\n"
                "VIEW-PNG,docs/design/image.png,pending,local template only\n")
            rows,stat=inventory(root)
            self.assertEqual(stat["format_plausible"],1)
            self.assertEqual(stat["customer_approved"],0)
            self.assertEqual(next(x["status"] for x in rows if x["id"]=="VIEW-PNG"),
                             "FORMAT_PLAUSIBLE_NOT_APPROVED")

    def test_procedural_note_is_only_a_note_not_handover_proof(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            (root/"docs/tz-audit").mkdir(parents=True)
            (root/"docs/handoff").mkdir()
            (root/"docs/tz-audit/requirements.psv").write_bytes(
                (ROOT/"docs/tz-audit/requirements.psv").read_bytes())
            (root/"docs/handoff/meeting.md").write_text(
                "Synthetic TEST evidence only; no actual museum meeting or approval exists.")
            (root/"docs/handoff/DESIGN_EVIDENCE.csv").write_text(
                "id,path,museum_approval,notes\n"
                "CONCEPT-DEMO,docs/handoff/meeting.md,pending,draft log\n")
            rows,summary=inventory(root)
            self.assertEqual(summary["format_plausible"],1)
            self.assertEqual(summary["customer_approved"],0)
            self.assertEqual(next(x["status"] for x in rows if x["id"]=="CONCEPT-DEMO"),
                             "FORMAT_PLAUSIBLE_NOT_APPROVED")

    def test_false_claimed_approval_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            (root/"docs/tz-audit").mkdir(parents=True)
            (root/"docs/handoff").mkdir()
            (root/"docs/tz-audit/requirements.psv").write_bytes(
                (ROOT/"docs/tz-audit/requirements.psv").read_bytes())
            evidence=(root/"docs/handoff/DESIGN_EVIDENCE.csv")
            evidence.write_text("id,path,museum_approval,notes\n"
                                "VIEW-PNG,,yes,not approved\n")
            with self.assertRaisesRegex(ValueError,"MUST NOT"):
                inventory(root)
            evidence.write_text("id,path,museum_approval,notes\n"
                                "VIEW-PNG,/etc/hosts,pending,absolute forbidden\n")
            with self.assertRaisesRegex(ValueError,"Unsafe"):
                inventory(root)

    def test_stale_generated_report_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            path=Path(temporary)/"matrix.csv"
            path.write_text("old")
            with self.assertRaisesRegex(ValueError,"stale"):
                require_matching_report(path,"new")
            path.write_text("new")
            require_matching_report(path,"new")

    def test_missing_required_variant_and_fake_tz_are_rejected(self):
        rows=define()
        req=tender_requirements(ROOT)
        with self.assertRaisesRegex(ValueError,"Missing original tender"):
            from dataclasses import replace
            check_design_catalog([replace(rows[0],tz="TZ-999")]+rows[1:],req)
        with self.assertRaisesRegex(ValueError,"Required distinct variant"):
            check_design_catalog([r for r in rows if r.id!="DISK-HDD"],req)

if __name__=="__main__":
    unittest.main()
