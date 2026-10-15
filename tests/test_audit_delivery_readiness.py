import tempfile
import unittest
from pathlib import Path

from scripts.audit_delivery_readiness import inspect, markdown


class DeliveryReadinessTests(unittest.TestCase):
    def test_real_tender_matrix_is_counted_without_acceptance_claim(self):
        root = Path(__file__).resolve().parents[1]
        data = inspect(root)
        self.assertEqual(data["tender_requirements"]["total"], 325)
        self.assertFalse(data["customer_acceptance"])
        self.assertFalse(data["exclusive_rights_transferred"])
        self.assertFalse(data["production_ready"])
        self.assertEqual(data["summary"]["missing_drafts"], 0)
        self.assertGreaterEqual(data["summary"]["independently_unverified_requirements"], 12)
        self.assertEqual(data["prepared_files"]["visitor_guide_draft"]["status"],
                         "DRAFT_PRESENT_NOT_CUSTOMER_ACCEPTED")
        self.assertIn("Not a signed acceptance", markdown(data))

    def test_missing_source_is_reported_as_missing_not_accepted(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            (folder / "docs/tz-audit").mkdir(parents=True)
            (folder / "docs/tz-audit/requirements.psv").write_bytes(
                (root / "docs/tz-audit/requirements.psv").read_bytes())
            data = inspect(folder)
            self.assertGreater(data["summary"]["missing_drafts"], 5)
            self.assertFalse(data["customer_acceptance"])

    def test_duplicate_requirement_id_is_rejected(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp) / "docs/tz-audit"
            folder.mkdir(parents=True)
            p = folder / "requirements.psv"
            content = (root / "docs/tz-audit/requirements.psv").read_text()
            p.write_text(content + content.splitlines()[1] + "\n")
            with self.assertRaisesRegex(ValueError, "duplicate"):
                inspect(Path(temp))


if __name__ == "__main__":
    unittest.main()
