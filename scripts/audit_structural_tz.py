#!/usr/bin/env python3
"""Audit exact structural TZ-175/252/262 obligations in the static public build.

Ignores ONLY the static-export sentinel for missing English translations (a
404 noindex fallback, not a published page); all other output pages, including
the genuine 404, must have an accessible route hierarchy and consistent layout.
"""
from __future__ import annotations

import html
import re
import sys
from pathlib import Path

STATIC = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("apps/web/out")
SENTINEL = "en/museum/not-translated/index.html"


def tag(content: str, name: str) -> bool:
    return bool(re.search(rf'<{name}\b', content, re.I))


def audit(root: Path) -> dict:
    pages = sorted(root.rglob("index.html"))
    if not pages:
        raise AssertionError(f"No static pages in {root}")
    missing: list[str] = []
    tested = 0
    error_pages = 0
    english_pages = 0
    en_sentinels = 0
    for path in pages:
        rel = path.relative_to(root).as_posix()
        if rel == SENTINEL:
            en_sentinels += 1
            # Next.js requires a route for an empty optional EN collection.
            # This route is 404 and noindex, not a visitor page.
            text = path.read_text(encoding="utf-8")
            if "noindex" not in text or "not-translated" not in text:
                missing.append(f"{rel}: English sentinel is not safely 404/noindex")
            continue
        tested += 1
        text = html.unescape(path.read_text(encoding="utf-8"))
        is_home = rel == "index.html"
        is_en = rel.startswith("en/")
        if is_en:
            english_pages += 1
        if rel.startswith(("404/", "_not-found/")):
            error_pages += 1
        for name in ("header", "footer", "main"):
            if not tag(text, name) or f'class="site-{name}"' not in text and name != "main":
                missing.append(f"{rel}: missing shared {name}")
        if not is_home:
            expected = 'aria-label="Breadcrumbs"' if is_en else 'aria-label="Хлебные крошки"'
            if expected not in text or 'aria-current="page"' not in text:
                missing.append(f"{rel}: breadcrumbs/current page missing")
            if 'href="/"' not in text:
                missing.append(f"{rel}: missing home breadcrumb link")
        for val in ("tel:+78122945082", "mailto:musbread@cult.gugov.spb.ru",
                    "https://vk.com/club37126776", "https://max.ru/id7808018523_gos"):
            if val not in text:
                missing.append(f"{rel}: missing footer contact/social {val[:22]}")
    if missing:
        raise AssertionError("\n".join(missing[:75]))
    return {
        "static_files": len(pages),
        "tested_visitor_pages": tested,
        "english_pages": english_pages,
        "error_pages": error_pages,
        "safe_unpublished_EN_sentinels": en_sentinels,
        "breadcrumbs_every_nonhome": True,
        "header_main_footer_every_page": True,
        "footer_contacts_and_social_every_page": True,
    }


if __name__ == "__main__":
    print("STRUCTURE TZ-175/252/262 PASS:", audit(STATIC))
