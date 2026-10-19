#!/usr/bin/env python3
"""Offline link-integrity gate for the full museum static website build.

Checks references from every exported HTML page against the actual artifact.
Does not crawl external sites or silently replace historic original content.
Three exact source URLs were independently observed as 403/404 on 2026-10-19;
these upstream failures are explicitly reported, never counted as passing links.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urljoin, urlsplit

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "apps/web/out"
ORIGIN = "https://muzei-xleb.ru"

# Actual unavailable links inherited from the original museum (checked on
# 2026-10-19). Preserve their source identity until the museum chooses a fix.
KNOWN_UPSTREAM_BROKEN = {
    "/node/462": "403 (original redirects to /afisha/2026-05, then returns 403)",
    "/sites/default/files/page/202110271242-prikaz_no94.pdf": "404 (original file absent)",
    "/obratnaya-svyaz": "403 (original anti-corruption feedback link restricted)",
}
LOCAL_TAG_ATTRS = {"a": "href", "img": "src", "script": "src",
                   "link": "href", "iframe": "src", "source": "src", "video": "src"}
LOCAL_HOSTS = {"muzei-xleb.ru", "www.muzei-xleb.ru"}


class References(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.references: list[tuple[str, str]] = []

    def handle_starttag(self, tag, attrs):
        attr = LOCAL_TAG_ATTRS.get(tag)
        if attr:
            url = dict(attrs).get(attr)
            if url:
                self.references.append((tag, url))


def is_file_in_static(out: Path, public_path: str) -> bool:
    relative = unquote(public_path).lstrip("/")
    if ".." in Path(relative).parts or "\x00" in relative:
        return False
    variants = (out / relative, out / relative / "index.html",
                out / (relative + ".html"))
    return any(candidate.is_file() for candidate in variants)


def audit(out: Path = OUT) -> dict:
    if not out.is_dir():
        raise RuntimeError(f"Missing offline museum build: {out}")
    summary = Counter()
    unexpected = defaultdict(list)
    known = Counter()
    pages = sorted(out.rglob("*.html"))
    for file in pages:
        parser = References()
        try:
            parser.feed(file.read_text(encoding="utf-8"))
        except Exception as exc:
            raise AssertionError(f"Broken HTML: {file}") from exc
        own_path = "/" + str(file.relative_to(out)).removesuffix("index.html")
        for tag, raw in parser.references:
            if raw.startswith(("#", "mailto:", "tel:", "data:", "javascript:")):
                continue
            url = urlsplit(urljoin(ORIGIN + own_path, raw))
            if url.netloc not in LOCAL_HOSTS or url.scheme not in ("http", "https"):
                continue
            path = url.path
            summary["checked_local_references"] += 1
            if is_file_in_static(out, path):
                summary["resolved_local_references"] += 1
            elif path in KNOWN_UPSTREAM_BROKEN and tag == "a":
                known[path] += 1
            elif len(unexpected[(tag, path)]) < 3:
                unexpected[(tag, path)].append(str(file.relative_to(out)))
    if unexpected:
        details = "\n".join(f"{tag} {path}: {', '.join(files)}" for (tag, path), files in sorted(unexpected.items()))
        raise AssertionError(f"UNEXPECTED BROKEN MUSEUM LOCAL LINKS:\n{details}")
    result = {
        "html_pages": len(pages),
        "checked_local_references": summary["checked_local_references"],
        "resolved_local_references": summary["resolved_local_references"],
        "known_upstream_breaks": sum(known.values()),
        "known_upstream_link_details": dict(sorted(known.items())),
        "unexpected_broken_local_links": 0,
    }
    if sum(known.values()) + summary["resolved_local_references"] != summary["checked_local_references"]:
        raise AssertionError("Internal museum links were not fully classified")
    print("MUSEUM_OFFLINE_LINKS_PASS", result, flush=True)
    return result


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--out", type=Path, default=OUT)
    audit(p.parse_args().out)
