#!/usr/bin/env python3
"""Check all internal anchor links and fragments in an exported Next.js site.

Scope: static HTML routes and in-page anchors; no external link requests.
"""
from __future__ import annotations

import argparse
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urljoin, urlsplit


class Anchors(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links: list[str] = []
        self.ids: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        data = dict(attrs)
        if data.get("id"):
            self.ids.add(data["id"])  # type: ignore[arg-type]
        if tag == "a" and data.get("href"):
            self.links.append(data["href"])  # type: ignore[arg-type]


def audit_links(root: Path) -> dict[str, int]:
    root = root.resolve()
    if not root.is_dir() or not (root / "index.html").is_file():
        raise ValueError("Missing built site/index.html")
    pages = sorted(root.rglob("*.html"))
    cache: dict[Path, Anchors] = {}

    def parsed(path: Path) -> Anchors:
        if path not in cache:
            parser = Anchors()
            parser.feed(path.read_text(encoding="utf-8"))
            cache[path] = parser
        return cache[path]

    errors: list[str] = []
    checked = 0
    for page in pages:
        relative = page.relative_to(root).as_posix()
        url_path = "/" + relative.removesuffix("index.html")
        for href in parsed(page).links:
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
            if not path.is_relative_to(root) or not path.is_file():
                errors.append(f"{url_path} -> {href} (missing static page)")
                continue
            if destination.fragment and unquote(destination.fragment) not in parsed(path).ids:
                errors.append(f"{url_path} -> {href} (missing anchor)")
                continue
            checked += 1

    if errors:
        raise ValueError(f"{len(errors)} broken internal links:\n" + "\n".join(errors[:40]))
    return {"pages": len(pages), "verified_internal_links": checked}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("build", type=Path)
    args = parser.parse_args()
    print("STATIC LINKS OK:", audit_links(args.build))


if __name__ == "__main__":
    main()
