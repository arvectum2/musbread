import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from scripts.check_php_fpm import FpmConfigurationError, examine


class PhpFpmRuntimeTests(unittest.TestCase):
    def run_mock(self, banner: str, listener: str):
        return [
            SimpleNamespace(stdout=banner, stderr=""),
            SimpleNamespace(stdout="", stderr=f"[notice] listen = {listener}\n"),
        ]

    def test_valid_fpm_binary_and_nginx_unix_socket_agree(self):
        with tempfile.TemporaryDirectory() as base:
            nginx = Path(base) / "private.conf"
            nginx.write_text("fastcgi_pass unix:/run/php/php8.4-fpm.sock;\n")
            with patch("scripts.check_php_fpm.subprocess.run", side_effect=self.run_mock(
                "PHP 8.4.27 (fpm-fcgi)", "/run/php/php8.4-fpm.sock"
            )):
                self.assertEqual(
                    examine("fpm", "/run/php/php8.4-fpm.sock", nginx),
                    ("8.4.27", "/run/php/php8.4-fpm.sock"),
                )

    def test_php_cli_and_older_fpm_are_never_accepted(self):
        for banner in ["PHP 8.4.27 (cli)", "PHP 8.3.29 (fpm-fcgi)", "php-fpm not installed"]:
            with self.subTest(banner=banner):
                with patch("scripts.check_php_fpm.subprocess.run", side_effect=self.run_mock(
                    banner, "/run/php/php8.4-fpm.sock"
                )):
                    with self.assertRaises(FpmConfigurationError):
                        examine("fake-fpm")

    def test_php2shell_unpatched_fpm_is_rejected(self):
        for version in ("8.4.26", "8.5.11", "8.6.0"):
            with self.subTest(version=version):
                with patch("scripts.check_php_fpm.subprocess.run", side_effect=self.run_mock(
                    f"PHP {version} (fpm-fcgi)", "/run/php/php8.4-fpm.sock"
                )):
                    with self.assertRaises(FpmConfigurationError):
                        examine("fpm")

    def test_wrong_pool_socket_is_rejected_even_when_php_version_is_new(self):
        with patch("scripts.check_php_fpm.subprocess.run", side_effect=self.run_mock(
            "PHP 8.4.27 (fpm-fcgi)", "127.0.0.1:9000"
        )):
            with self.assertRaisesRegex(FpmConfigurationError, "listener"):
                examine("fpm", "/run/php/php8.4-fpm.sock")

    def test_multiple_pools_need_explicit_configuration(self):
        with patch("scripts.check_php_fpm.subprocess.run", side_effect=[
            SimpleNamespace(stdout="PHP 8.4.27 (fpm-fcgi)", stderr=""),
            SimpleNamespace(stdout="listen = 127.0.0.1:9000\nlisten = /run/php/php8.4-fpm.sock\n", stderr=""),
        ]):
            with self.assertRaisesRegex(FpmConfigurationError, "Exactly one"):
                examine("fpm")


if __name__ == "__main__":
    unittest.main()
