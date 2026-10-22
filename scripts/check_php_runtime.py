#!/usr/bin/env python3
"""Block vulnerable PHP runtimes (PHP2Shell, 2026-10-21); checks local binary only."""
from __future__ import annotations

import argparse
import re
import subprocess

# CVE-2026-109618 and CVE-2026-109619. Unknown/EOL branches fail closed.
MIN_SAFE_PATCH = {(8, 2): 35, (8, 3): 36, (8, 4): 27, (8, 5): 12}


def check_version(version: str) -> bool:
    match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", version)
    if match is None:
        return False
    major, minor, patch = (int(v) for v in match.groups())
    minimum = MIN_SAFE_PATCH.get((major, minor))
    return minimum is not None and patch >= minimum


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", default="php", help="PHP executable to validate")
    args = parser.parse_args()
    try:
        result = subprocess.run([args.binary, "-v"], capture_output=True, text=True, timeout=10, check=True)
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        parser.exit(1, "PHP SECURITY GATE FAILED: cannot execute PHP runtime\n")
    match = re.search(r"\bPHP (\d+\.\d+\.\d+)\b", result.stdout + result.stderr)
    version = match.group(1) if match else "(unrecognized)"
    if not check_version(version):
        parser.exit(1, f"PHP SECURITY GATE FAILED: vulnerable or unapproved PHP {version}; see PHP2Shell advisory from 21 October 2026\n")
    print(f"PHP SECURITY GATE OK: {version} (CVE-2026-109618/109619 patched)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
