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
# On-demand source-backed React Flight DATA is not a shared application bundle.
# Preserve independent per-page transfer budgets and the 2 MiB code budget.
MAX_HYDRATION_ASSET = 768 * 1024
MAX_HYDRATION_PAGE = 768 * 1024
HYDRATION_PATH = "_next/static/musbread-inline/"
MAX_MEDIA_FILE = 5 * 1024 * 1024
MEDIA_SUFFIXES = {".webp", ".avif", ".png", ".jpg", ".jpeg", ".gif", ".mp4", ".webm"}


class _PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.issues: list[str] = []
        self.hydration_scripts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        properties = dict(attrs)
        if tag == "script":
            src = properties.get("src") or ""
            if src.startswith("/" + HYDRATION_PATH):
                self.hydration_scripts.append(src.removeprefix("/"))
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
    max_page_data = 0
    hydration_page_count = 0
    hydration_paths: set[str] = set()
    for page in pages:
        if page.is_symlink():
            problems.append("HTML symlink not allowed: " + str(page.relative_to(root)))
            continue
        parser = _PageParser()
        parser.feed(page.read_text(encoding="utf-8"))
        for error in parser.issues:
            problems.append(str(page.relative_to(root)) + ": " + error)
        payload_size = 0
        if parser.hydration_scripts:
            hydration_page_count += 1
        for source in set(parser.hydration_scripts):
            hydration_paths.add(source)
            asset = root / source
            if not asset.is_file() or asset.is_symlink():
                problems.append("Missing or unsafe page hydration payload: " + source)
                continue
            payload_size += asset.stat().st_size
        max_page_data = max(max_page_data, payload_size)
        if payload_size > MAX_HYDRATION_PAGE:
            problems.append("Oversized per-page React data transfer: "
                            + str(page.relative_to(root)))
    js = sorted(root.rglob("*.js"))
    js_total = 0
    js_inventory_total = 0
    hydration_total = 0
    hydration_files = 0
    for asset in js:
        if asset.is_symlink():
            problems.append("JavaScript symlink not allowed")
            continue
        size = asset.stat().st_size
        js_inventory_total += size
        relative = asset.relative_to(root).as_posix()
        if relative.startswith(HYDRATION_PATH):
            hydration_total += size
            hydration_files += 1
            if size > MAX_HYDRATION_ASSET:
                problems.append("Oversized page hydration content asset: " + relative)
            if relative not in hydration_paths:
                problems.append("Unreferenced public hydration script: " + relative)
        else:
            js_total += size
            if size > MAX_JS_CHUNK:
                problems.append("Oversized application JS chunk: " + relative)
    if js_total > MAX_JS_TOTAL:
        problems.append("Total application JavaScript exceeds 2 MiB")
    media = [p for p in root.rglob("*") if p.suffix.lower() in MEDIA_SUFFIXES and p.is_file()]
    for asset in media:
        if asset.is_symlink() or asset.stat().st_size > MAX_MEDIA_FILE:
            problems.append("Oversized or symlinked media: " + str(asset.relative_to(root)))
    return {
        "html_pages": len(pages), "js_files": len(js),
        "js_bytes_total": js_total,  # original <=2 MiB compiled application code budget
        "js_inventory_bytes_total": js_inventory_total,
        "hydration_data_bytes_total": hydration_total,
        "hydration_data_assets": hydration_files,
        "hydration_pages": hydration_page_count,
        "max_per_page_hydration_bytes": max_page_data,
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
