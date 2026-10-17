#!/usr/bin/env python3
"""TZ-224: read-only PHP-FPM 8.4+ startup and Nginx socket compatibility gate.

Checks actual fpm-fcgi executable and its parsed config, NOT only php-cli.
On Mac mini, run with --binary /opt/homebrew/sbin/php-fpm; this is local QA.
On Linux provide --expected-listen /run/php/php8.4-fpm.sock.
"""
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
from pathlib import Path


class FpmConfigurationError(ValueError):
    pass


def examine(
    executable: str,
    expected_listen: str | None = None,
    nginx_template: Path | None = None,
) -> tuple[str, str]:
    try:
        version = subprocess.run(
            [executable, "-v"], capture_output=True, text=True, timeout=10, check=True
        )
        config = subprocess.run(
            [executable, "-tt"], capture_output=True, text=True, timeout=15, check=True
        )
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise FpmConfigurationError("PHP-FPM executable or its configuration failed verification") from exc

    banner = version.stdout + version.stderr
    match = re.search(r"PHP\s+(\d+)\.(\d+)\.(\d+).*?fpm-fcgi", banner, re.I | re.S)
    if match is None or tuple(map(int, match.groups())) < (8, 4, 0):
        raise FpmConfigurationError("An actual PHP-FPM (fpm-fcgi) executable 8.4+ is required")

    details = config.stdout + config.stderr
    listeners = re.findall(r"\blisten\s*=\s*([^\s]+)", details)
    if len(listeners) != 1:
        raise FpmConfigurationError("Exactly one configured PHP-FPM pool listener is required for this template")
    actual = listeners[0]

    if expected_listen is not None and actual != expected_listen:
        raise FpmConfigurationError("FPM listener does not match the approved expected socket")
    if nginx_template is not None:
        text = nginx_template.read_text(encoding="utf-8")
        endpoints = re.findall(r"^\s*fastcgi_pass\s+unix:([^;\s]+);", text, re.M)
        if len(endpoints) != 1 or actual != endpoints[0]:
            raise FpmConfigurationError("Nginx FastCGI socket differs from actual PHP-FPM pool")

    return ".".join(match.groups()), actual


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", default=None, help="Actual FPM executable, not PHP CLI")
    parser.add_argument("--expected-listen", default=None, help="Expected FPM pool socket or host:port")
    parser.add_argument("--nginx-template", type=Path, default=None)
    args = parser.parse_args()
    executable = args.binary or shutil.which("php-fpm8.4") or shutil.which("php-fpm")
    if executable is None:
        parser.exit(1, "PHP-FPM 8.4+ runtime not installed or not in PATH\n")
    try:
        version, listener = examine(executable, args.expected_listen, args.nginx_template)
    except (FpmConfigurationError, OSError):
        parser.exit(1, "PHP-FPM VERIFICATION FAILED: version, pool, or Nginx listener mismatch\n")
    print(f"PHP-FPM OK (actual fpm-fcgi {version}; listener {listener})")
    print("This verifies a local executable and its configuration, not a running production backend.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
