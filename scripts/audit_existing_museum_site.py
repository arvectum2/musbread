#!/usr/bin/env python3
"""Pre-release source-first check against the existing museum site (run on Mac mini).
No credentials, document downloads, third-party policies, or fabricated legal text.
This checks HTTP HEAD, current HTML document references and official staff names.
It does NOT certify the legal version or authorize public release.
"""
from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import subprocess
from urllib.parse import urljoin, urlparse
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://muzei-xleb.ru"
DOC_PAGES = {
    "founding": "/oficialnye-dokumenty-muzeya",
    "privacy": "/politika-konfidencialnosti-i-obrabotki-personalnyh-dannyh",
    "visiting": "/ceny-i-usloviya-predostavleniya-uslug",
}

class LinksAndText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links: set[str] = set()
        self.parts: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            href = dict(attrs).get("href")
            if href:
                url = urljoin(BASE + "/", href)
                if urlparse(url).netloc in {"muzei-xleb.ru", "www.muzei-xleb.ru"}:
                    self.links.add(urlparse(url).path)

    def handle_data(self, data):
        self.parts.append(data)


def site_html(path: str) -> LinksAndText:
    with urlopen(BASE + path, timeout=12) as response:
        if response.status != 200:
            raise RuntimeError(f"GET {path}: HTTP {response.status}")
        parser = LinksAndText()
        parser.feed(response.read(4_000_000).decode("utf-8", "replace"))
        return parser


def check_url(path: str):
    proc = subprocess.run(
        ["curl", "-4", "-L", "-I", "-sS", "--connect-timeout", "6", "--max-time", "12", "-o", "/dev/null",
         "-w", "%{http_code}|%{content_type}|%{url_effective}", BASE + path],
        capture_output=True, text=True, timeout=15,
    )
    fields = proc.stdout.strip().split("|", 2)
    status = int(fields[0]) if fields[0].isdigit() else 0
    final = fields[2] if len(fields) > 2 else ""
    correct_origin = urlparse(final).netloc in {"muzei-xleb.ru", "www.muzei-xleb.ru"}
    ext = Path(path).suffix.lower()
    content_type = fields[1].lower() if len(fields) > 1 else ""
    type_ok = (ext != ".pdf" or content_type.startswith("application/pdf")) and (
        ext != ".docx" or "wordprocessingml.document" in content_type
    )
    return {"path": path, "http": status, "type": content_type,
            "origin_ok": correct_origin, "type_ok": type_ok,
            "ok": proc.returncode == 0 and status == 200 and correct_origin and type_ok}


def main() -> int:
    args = argparse.ArgumentParser()
    args.add_argument("--output", type=Path)
    options = args.parse_args()
    data = json.loads((ROOT / "apps/cms/database/reference-museum-sections.json").read_text())
    if data["source"].rstrip("/") != BASE:
        raise RuntimeError("Unexpected source host in CMS seed")
    section_urls = {row["legacy_path"] for row in data["sections"] if row["legacy_path"]}
    docs_ts = (ROOT / "apps/web/src/data/museum-official-documents.ts").read_text()
    doc_urls = set(re.findall(r'official\("(/sites/default/files/[^"]+)"\)', docs_ts))
    # A public news link is shown separately from the CMS menu; verify that
    # exact museum-reference URL too, without inventing a second news catalog.
    reference_source = (ROOT / "apps/web/src/data/museum-reference.ts").read_text()
    news_match = re.search(r'newsUrl:\s*"https://muzei-xleb\.ru(/[^"]+)"', reference_source)
    if news_match is None:
        raise RuntimeError("Missing or non-official source URL for museum news")
    additional_source_urls = {news_match.group(1)}
    all_urls = sorted(section_urls | doc_urls | additional_source_urls)
    with ThreadPoolExecutor(max_workers=5) as pool:
        checks = list(pool.map(check_url, all_urls))
    stale_references = []
    for group, source in DOC_PAGES.items():
        slice_text = docs_ts.split("const " + group + ":")[1].split("\n};")[0]
        curated_paths = re.findall(r'url:official\("(/sites/default/files/[^"]+)"\)', slice_text)
        origin = site_html(source)
        for path in curated_paths:
            if path not in origin.links:
                stale_references.append({"source": source, "missing_document": path})

    # The official administrator directory is publicly listed, but all changes
    # must be confirmed before releasing the new museum site.
    html = site_html("/administraciya")
    staff = (ROOT / "apps/web/src/data/museum-team.ts").read_text()
    names = re.findall(r'name:"([^"]+)"', staff)
    page_text = " ".join(" ".join(html.parts).split())
    missing_staff = [name for name in names if name not in page_text]
    status = Counter("OK" if x["ok"] else "FAIL" for x in checks)
    ok = not stale_references and not missing_staff and not status.get("FAIL")
    report = {
        "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": BASE, "sections_with_source": len(section_urls),
        "additional_reference_pages": sorted(additional_source_urls),
        "curated_document_links": len(doc_urls),
        "document_groups_checked": list(DOC_PAGES),
        "administration_roles_checked": len(names),
        "ok": ok, "http_results": dict(status),
        "unreachable_or_wrong_type": [x for x in checks if not x["ok"]],
        "orphan_document_links": stale_references,
        "names_not_on_official_page": missing_staff,
        "disclaimer": "HTTP and HTML match, not legal currency or permission to publish",
    }
    if options.output:
        options.output.parent.mkdir(parents=True, exist_ok=True)
        options.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if ok else 1

if __name__ == "__main__":
    raise SystemExit(main())
