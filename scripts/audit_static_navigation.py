#!/usr/bin/env python3
"""Check static navigation, fragments and explicit Tab order for public links.

All exported internal/external anchors must be sequentially focusable by
native macOS WebKit (explicit tabindex=0), never through a JS keyboard hack.
"""
from __future__ import annotations

import argparse
import json
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urljoin, urlsplit


class Anchors(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links: list[tuple[str, str | None]] = []
        self.ids: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        data = dict(attrs)
        if data.get("id"):
            self.ids.add(data["id"])  # type: ignore[arg-type]
        if tag == "a" and data.get("href"):
            self.links.append((data["href"], data.get("tabindex")))  # type: ignore[arg-type]


def audit_links(root: Path, private_document_manifest: Path | None = None) -> dict[str, int]:
    root = root.resolve()
    if not root.is_dir() or not (root / "index.html").is_file():
        raise ValueError("Missing built site/index.html")
    pages = sorted(root.rglob("*.html"))
    known_private={}
    if private_document_manifest is not None:
        source=json.loads(private_document_manifest.read_text(encoding="utf-8"))
        entries=source.get("files",[])
        if source.get("source")!="https://muzei-xleb.ru" or len(entries)!=source.get("count") or len(entries)!=101:
            raise ValueError("Original museum document manifest lacks full verified provenance")
        for item in entries:
            url=item.get("legacy_path", "")
            if (not url.startswith("/sites/default/files/") or ".." in url
                    or item.get("url")!="https://muzei-xleb.ru"+url
                    or not re.fullmatch(r"[a-f0-9]{64}",item.get("sha256", ""))
                    or not isinstance(item.get("size_bytes"),int) or item["size_bytes"]<1
                    or item.get("format") not in ("pdf","docx") or not url.endswith("."+item["format"])):
                raise ValueError("Unverified private archived original URL " + url)
            if url in known_private:raise ValueError("Duplicate original path: "+url)
            known_private[url]=item
    cache: dict[Path, Anchors] = {}

    def parsed(path: Path) -> Anchors:
        if path not in cache:
            parser = Anchors()
            parser.feed(path.read_text(encoding="utf-8"))
            cache[path] = parser
        return cache[path]

    errors: list[str] = []
    checked = 0
    private_original_links = 0
    for page in pages:
        relative = page.relative_to(root).as_posix()
        url_path = "/" + relative.removesuffix("index.html")
        for href, tabindex in parsed(page).links:
            if tabindex != "0":
                errors.append(f"{url_path} -> {href} (missing safe sequential tabindex=0)")
            if href.lower().startswith("javascript:"):
                errors.append(f"{url_path} -> forbidden JavaScript URL")
                continue
            destination = urlsplit(urljoin("https://musbread.invalid" + url_path, href))
            if destination.scheme not in ("http", "https") or destination.netloc != "musbread.invalid":
                continue
            path = root / unquote(destination.path).lstrip("/")
            if destination.path.endswith("/"):
                path = path / "index.html"
            elif not path.is_file():
                path = path / "index.html"
            path = path.resolve()
            if (private_document_manifest is not None and path.is_relative_to(root)
                    and not path.is_file() and not destination.fragment
                    and destination.path in known_private):
                private_original_links += 1
                continue
            if not path.is_relative_to(root) or not path.is_file():
                errors.append(f"{url_path} -> {href} (missing static page)")
                continue
            if destination.fragment and unquote(destination.fragment) not in parsed(path).ids:
                errors.append(f"{url_path} -> {href} (missing anchor)")
                continue
            checked += 1

    if errors:
        raise ValueError(f"{len(errors)} unsafe public links / broken navigation:\n" + "\n".join(errors[:40]))
    result={"pages": len(pages), "verified_internal_links": checked}
    if private_document_manifest is not None:
        result["source_manifest_only_links_not_present_in_CI_export"]=private_original_links
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("build", type=Path)
    parser.add_argument("--private-document-manifest",type=Path,
                        help="Git-only CI: disclose missing private originals exactly from pinned 101-document manifest")
    args = parser.parse_args()
    print("STATIC LINKS OK:", audit_links(args.build,args.private_document_manifest))


if __name__ == "__main__":
    main()
