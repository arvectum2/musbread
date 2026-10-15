#!/usr/bin/env python3
"""Conservative CI check for paragraph/headline font-size units in authored CSS."""
from __future__ import annotations
import argparse
import re
from pathlib import Path

FONT = re.compile(r"(?i)(?<![-\w])font-size\s*:\s*([^;}]+)[;}]")
FORBIDDEN = re.compile(r"(?i)(?<![\w-])\d+(?:\.\d+)?\s*(px|pt|vw|vh|vmin|vmax|%)\b")
VALID_FONT = re.compile(r"(?i)(?:^|[(:+\-\s,])(?:\d*\.?\d+)\s*(rem|em)\b")

def disallowed(text: str) -> list[str]:
    css = re.sub(r"/\*[\s\S]*?\*/", "", text)
    bad: list[str] = []
    for match in FONT.finditer(css):
        val = match.group(1).strip()
        if FORBIDDEN.search(val) or (not VALID_FONT.search(val) and val not in {"inherit", "initial", "unset", "revert"}):
            bad.append(val)
    return bad

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("files", nargs="*", type=Path,
                        default=[Path("apps/web/src/app/globals.scss")])
    args = parser.parse_args()
    errors = [(str(path), disallowed(path.read_text(encoding="utf-8"))) for path in args.files]
    bad = [(name, problems) for name, problems in errors if problems]
    if bad:
        for name, problems in bad:
            print(name, "FORBIDDEN font-size declarations:", problems)
        raise SystemExit(1)
    print("CSS font-size check passed for", len(errors), "stylesheets (rem/em only).")

if __name__ == "__main__":
    main()
