import json
import shutil
import tempfile
import unittest
from pathlib import Path

from scripts.audit_final_formats import ROOT, FINAL, report, markdown


class FormatReadinessAuditTests(unittest.TestCase):
    def test_all_technical_formats_are_real_but_no_final_approved_items(self):
        data=report(ROOT)
        self.assertEqual(data["technical_file_counts"],{"svg":42,"pdf":26,"png":16,"pptx":2})
        self.assertEqual(data["target_design_items"],113)
        self.assertEqual(data["approved_design_items"],0)
        self.assertFalse(data["production_print_ready"])
        self.assertFalse(data["real_museum_brand_available"])
        self.assertEqual(len(data["formats"]),10)
        self.assertEqual({x["required_extension"] for x in data["formats"]},set(FINAL))
        self.assertEqual({x["final_customer_approved_format"] for x in data["formats"]},{"NOT_PROVIDED"})
        self.assertIn("not",markdown(data).lower())

    def test_tampered_png_refused_even_if_filename_and_extension_valid(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            relative="docs/design/technical-drafts"
            shutil.copytree(ROOT/relative,root/relative)
            p=root/"docs/design/technical-drafts/digital-merch/TECH_VK-AVATAR.png"
            contents=bytearray(p.read_bytes()); contents[-28]^=0x5
            p.write_bytes(contents)
            with self.assertRaisesRegex(ValueError,"manifest"):
                report(root)

    def test_missing_required_pptx_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            relative="docs/design/technical-drafts"
            shutil.copytree(ROOT/relative,root/relative)
            (root/relative/"TECH_SLIDES_4x3.pptx").unlink()
            from pptx.exc import PackageNotFoundError
            with self.assertRaises((ValueError,FileNotFoundError,PackageNotFoundError)):
                report(root)


if __name__=="__main__":
    unittest.main()
