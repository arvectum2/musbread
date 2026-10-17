#!/usr/bin/env python3
"""TZ-242 objective, read-only static UI performance/privacy guard.

No third-party scripts, silent autoplay, embeds, or outsized static media.
A budget is not a Lighthouse measurement or a customer-approved design.
"""
from __future__ import annotations

import argparse
from html.parser import HTMLParser
import json
from pathlib import Path
from urllib.parse import urlsplit

MAX_JS_TOTAL = 2 * 1024 * 1024
MAX_JS_CHUNK = 512 * 1024
MAX_MEDIA_FILE = 5 * 1024 * 1024
MEDIA_SUFFIXES = {".webp", ".avif", ".png", ".jpg", ".jpeg", ".gif", ".mp4", ".webm"}


class _PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.issues: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        properties = dict(attrs)
        if tag == "script":
            src = properties.get("src") or ""
            if src.startswith("//") or urlsplit(src).scheme in ("http", "https"):
                self.issues.append("External script: " + src[:110])
            elif src and (src.startswith("data:") or src.startswith("javascript:")):
                self.issues.append("Unsafe script source")
        if tag in {"iframe", "object", "embed", "marquee", "blink"}:
            self.issues.append("Embedded or distracting tag: " + tag)
        if tag in {"video", "audio"} and "autoplay" in properties:
            self.issues.append("Autoplay media: " + tag)
        # Don't load invisible gallery assets eagerly before actual approval.
        if tag == "link" and properties.get("rel") == "preload" and properties.get("as") == "video":
            self.issues.append("Preloaded video")
        if tag == "img" and (properties.get("src") or "").startswith("data:"):
            value = properties.get("src") or ""
            if len(value) > 2048:
                self.issues.append("Heavy inline data image")


def audit(root: Path) -> dict:
    if not root.is_dir() or not (root / "index.html").is_file():
        raise ValueError("Point to a completed static site export containing index.html")
    problems: list[str] = []
    pages = sorted(root.rglob("*.html"))
    for page in pages:
        if page.is_symlink():
            problems.append("HTML symlink not allowed: " + str(page.relative_to(root)))
            continue
        parser = _PageParser()
        parser.feed(page.read_text(encoding="utf-8"))
        for error in parser.issues:
            problems.append(str(page.relative_to(root)) + ": " + error)
    js = sorted(root.rglob("*.js"))
    js_total = 0
    for asset in js:
        if asset.is_symlink():
            problems.append("JavaScript symlink not allowed")
            continue
        size = asset.stat().st_size
        js_total += size
        if size > MAX_JS_CHUNK:
            problems.append("Oversized JS chunk: " + str(asset.relative_to(root)))
    if js_total > MAX_JS_TOTAL:
        problems.append("Total shipped JavaScript exceeds 2 MiB")
    media = [p for p in root.rglob("*") if p.suffix.lower() in MEDIA_SUFFIXES and p.is_file()]
    for asset in media:
        if asset.is_symlink() or asset.stat().st_size > MAX_MEDIA_FILE:
            problems.append("Oversized or symlinked media: " + str(asset.relative_to(root)))
    return {
        "html_pages": len(pages), "js_files": len(js), "js_bytes_total": js_total,
        "media_files": len(media), "issues": problems,
        "status": "PASS" if not problems else "FAIL",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    result = audit(args.root)
    print("TZ-242 STATIC LIGHTWEIGHT UI: " + json.dumps(result, ensure_ascii=False))
    if result["issues"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
