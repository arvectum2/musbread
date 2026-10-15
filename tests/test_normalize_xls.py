"""Regression tests for values-only synthetic legacy XLS -> normalized XLSX."""
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "normalize_xls.py"
SOURCE = ROOT / "tests" / "fixtures" / "synthetic-legacy.xls"


class LegacyXlsTests(unittest.TestCase):
    def test_values_only_workbook_does_not_contain_executable_formulas(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / "normalized.xlsx"
            result = subprocess.run([sys.executable, str(SCRIPT), "--input", str(SOURCE),
                                     "--output", str(out)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            with zipfile.ZipFile(out) as archive:
                names = archive.namelist()
                self.assertIn("xl/workbook.xml", names)
                self.assertIn("xl/worksheets/sheet1.xml", names)
                self.assertFalse(any("vbaProject" in name or "externalLinks" in name for name in names))
                data = archive.read("xl/worksheets/sheet1.xml")
                ET.fromstring(data)
                self.assertIn(b"HYPERLINK", data)
                self.assertIn(b'Ticket test', data)
                self.assertNotIn(b"<f>", data)
                self.assertIn(b't="inlineStr"', data)

    def test_corrupt_container_is_rejected_and_cleans_output(self):
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            source = directory / "bad.xls"
            source.write_bytes(b"not a valid XLS" * 20)
            out = directory / "bad.xlsx"
            result = subprocess.run([sys.executable, str(SCRIPT), "--input", str(source),
                                     "--output", str(out)], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(out.exists())


if __name__ == "__main__":
    unittest.main()
