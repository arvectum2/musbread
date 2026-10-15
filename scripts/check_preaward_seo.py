#!/usr/bin/env python3
"""Prevent search engines from indexing unapproved museum pages."""
from pathlib import Path
import sys

def check(out: Path) -> None:
    robots = (out / "robots.txt").read_text(encoding="utf-8")
    sitemap = (out / "sitemap.xml").read_text(encoding="utf-8")
    homepage = (out / "index.html").read_text(encoding="utf-8")
    if "Disallow: /" not in robots:
        raise AssertionError("Draft robots.txt must deny indexing")
    if "<url>" in sitemap:
        raise AssertionError("Draft sitemap.xml must not contain unapproved pages")
    if 'name="robots"' not in homepage or "noindex" not in homepage:
        raise AssertionError("Draft homepage must be noindex")
    print("PREAWARD SEO SAFETY PASSED: robots disallow /, noindex and empty sitemap")

if __name__ == "__main__":
    check(Path(sys.argv[1]) if len(sys.argv) > 1 else Path("apps/web/out"))
