"""Prevent unreviewed removal of private archive regression gates."""
import sys
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from run_ci_python_tests import ARCHIVE_TESTS, test_files as collect_profile

class CIProfilesTests(unittest.TestCase):
    def test_disjoint_profiles_cover_all_discovered_files(self):
        all_tests = set(collect_profile("all"))
        public = set(collect_profile("public"))
        archive = set(collect_profile("archive"))
        self.assertEqual(public | archive, all_tests)
        self.assertFalse(public & archive)
        self.assertEqual(len(archive), len(ARCHIVE_TESTS))
        self.assertIn(ROOT / "tests" / "test_two_vm_request_ingress.py", public)
        self.assertIn(ROOT / "tests" / "test_externalize_inline_scripts.py", public)
        self.assertIn(ROOT / "tests" / "test_complete_museum_static_release.py", archive)

if __name__ == "__main__": unittest.main()
