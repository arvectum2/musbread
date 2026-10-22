import unittest
from scripts.check_php_runtime import check_version


class PhpSecurityRuntimeTests(unittest.TestCase):
    def test_affected_and_fixed_versions(self):
        for version in ("8.2.34", "8.3.35", "8.4.26", "8.5.11", "8.1.99", "8.6.0", "bad"):
            with self.subTest(version=version):
                self.assertFalse(check_version(version))
        for version in ("8.2.35", "8.3.36", "8.4.27", "8.5.12", "8.4.28"):
            with self.subTest(version=version):
                self.assertTrue(check_version(version))


if __name__ == "__main__":
    unittest.main()
