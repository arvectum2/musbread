#!/usr/bin/env python3
"""Pre-award STATIC markup/content gate, not a ГОСТ/PDF-UA certification.

Checks every export HTML page and optionally the CMS JSON snapshot.
No network, no cookies, no PII, no user authentication, no false claim that
PDF content is accessible. JSON and Markdown reports are intentionally factual.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

FORM_FIELDS = {"input", "textarea", "select"}
IMAGE_FILES = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
DOC_NAME = re.compile(r"^/documents/([a-f0-9]{64})\.(pdf|docx|xlsx)$")
LANGUAGES = {"ru", "en"}

# TZ-194: mechanical guard; a human still verifies truthfulness of the text.
ALT_GENERIC = re.compile(r"(?<![\w])(?:картинк[а-яё]*|изображени[а-яё]*|фотографи[а-яё]*|фото|график[а-яё]*|picture|image|photo|graphic|graph)(?![\w])", re.I)



class Page(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.nodes: list[tuple[str, dict[str, str]]] = []
        self.headers: list[str] = []
        self.texts: list[str] = []
        self.title = ""
        self._inside_title = False
        self._inside_heading = 0
        self.heading_text = ""
        self.h1_texts: list[str] = []

    def handle_starttag(self, tag: str, raw: list[tuple[str, str | None]]) -> None:
        attrs = {k: v or "" for k, v in raw}
        self.nodes.append((tag, attrs))
        if tag == "title":
            self._inside_title = True
        if tag == "h1":
            self._inside_heading += 1
        if tag == "h2":
            self.headers.append("h2")
        if tag == "h3":
            self.headers.append("h3")

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._inside_title = False
        if tag == "h1" and self._inside_heading:
            self.h1_texts.append(self.heading_text.strip())
            self.heading_text = ""
            self._inside_heading -= 1

    def handle_data(self, data: str) -> None:
        if self._inside_title:
            self.title += data
        if self._inside_heading:
            self.heading_text += data
        if data.strip():
            self.texts.append(data.strip())

    def elements(self, tag: str) -> list[dict[str, str]]:
        return [a for t, a in self.nodes if t == tag]


def issue(code: str, page: str, detail: str) -> dict[str, str]:
    return {"code": code, "page": page, "detail": detail}


def scan_page(html_path: Path, relative: str) -> tuple[list[dict], list[dict], Page]:
    errors: list[dict] = []
    warnings: list[dict] = []
    parser = Page()
    parser.feed(html_path.read_text(encoding="utf-8"))
    html = parser.elements("html")
    meta = parser.elements("meta")
    if relative == "en/museum/not-translated/index.html":
        # Static Next.js builds this 404 fallback even with zero translations.
        # Production nginx intercepts the URL and returns real HTTP 404.
        if not any("noindex" in m.get("content", "") for m in meta if m.get("name") == "robots"):
            errors.append(issue("SENTINEL_INDEXABLE", relative, "Technical fallback must be noindex"))
        return errors, warnings, parser

    if len(html) != 1:
        errors.append(issue("HTML_ROOT", relative, "Expected one HTML root"))
    else:
        expected = "en" if relative.startswith("en/") else "ru"
        if html[0].get("lang") != expected:
            errors.append(issue("LANG_MISMATCH", relative, f"Expected html lang={expected}"))
    if len(parser.elements("main")) != 1:
        errors.append(issue("MAIN_LANDMARK", relative, "Expected exactly one main element"))
    ids = [a["id"] for _, a in parser.nodes if a.get("id")]
    if "main" not in ids:
        errors.append(issue("MAIN_ID", relative, 'Missing main id="main"'))
    if len(ids) != len(set(ids)):
        errors.append(issue("DUPLICATE_ID", relative, "Duplicate id in page"))
    if len(parser.h1_texts) != 1 or not parser.h1_texts[0]:
        errors.append(issue("HEADING_H1", relative, "Expected one nonempty H1"))
    if not parser.title.strip():
        errors.append(issue("EMPTY_TITLE", relative, "Missing nonempty title"))
    if len(parser.title) > 125:
        warnings.append(issue("LONG_TITLE", relative, f"Title is {len(parser.title)} characters"))
    for img in parser.elements("img"):
        if "alt" not in img:
            errors.append(issue("IMG_MISSING_ALT", relative, img.get("src", "unknown image")[:140]))
        elif img["alt"] and (len(img["alt"]) > 125 or ALT_GENERIC.search(img["alt"])):
            errors.append(issue("ALT_POLICY", relative, img.get("src", "unknown image")[:140]))
    for link in parser.elements("a"):
        href = link.get("href", "")
        if href.startswith("javascript:"):
            errors.append(issue("SCRIPT_LINK", relative, href[:50]))
        if link.get("target") == "_blank":
            rel = set(link.get("rel", "").split())
            if not {"noopener", "noreferrer"} & rel:
                errors.append(issue("EXTERNAL_TARGET_REL", relative, href[:140]))
    if not any(a.get("href") == "#main" for a in parser.elements("a")):
        errors.append(issue("SKIP_LINK", relative, 'Missing keyboard skip link to #main'))
    labels = {x.get("for") for x in parser.elements("label") if x.get("for")}
    for tag in FORM_FIELDS:
        for field in parser.elements(tag):
            typ = field.get("type", "").lower()
            if typ in {"hidden", "submit", "button", "reset", "image"}:
                continue
            if "aria-label" not in field and "aria-labelledby" not in field and field.get("id") not in labels:
                errors.append(issue("UNLABELLED_FIELD", relative, f"{tag} id={field.get('id','')}"))
    if not any(m.get("name") == "viewport" for m in meta):
        errors.append(issue("MISSING_VIEWPORT", relative, "Missing mobile viewport"))
    if not any(m.get("name") == "robots" and "noindex" in m.get("content", "") for m in meta):
        warnings.append(issue("NOT_PREAWARD_NOINDEX", relative, "Pre-award page is not noindex"))
    return errors, warnings, parser


def audit(root: Path, snapshot: Path | None = None,
          strict_documents: bool = False) -> dict:
    root = root.resolve()
    if not (root / "index.html").is_file():
        raise ValueError("Missing static build index.html")
    errors: list[dict] = []
    warnings: list[dict] = []
    pages = sorted(root.rglob("*.html"))
    seen_images = set()
    for html in pages:
        relative = html.relative_to(root).as_posix()
        err, warn, page = scan_page(html, relative)
        errors.extend(err)
        warnings.extend(warn)
        for image in page.elements("img"):
            seen_images.add(image.get("src", ""))
    checked_documents = 0
    checked_entries = 0
    if snapshot:
        obj = json.loads(snapshot.read_text(encoding="utf-8"))
        if not isinstance(obj.get("entries"), list):
            raise ValueError("Snapshot must contain an entries array")
        # TZ-185/186/187: all approved SEO overrides must target a real
        # generated HTML route, with the actual emitted title/description/H1.
        # Empty/draft overrides are not exported. Existing CMS section fields
        # take precedence on a matching /guide/{slug}/ route.
        fixed = obj.get("fixed_page_seo", {})
        if not isinstance(fixed, dict):
            errors.append(issue("FIXED_SEO_SCHEMA", "(snapshot)", "Expected a route-to-metadata object"))
        else:
            published_sections = {x.get("slug"): x for x in obj.get("sections", [])
                                  if isinstance(x, dict)}
            for route, fields in fixed.items():
                if not isinstance(route, str) or not re.fullmatch(
                    r"/|/(?:museum|news|excursions|exhibitions|documents|search|events)/|/guide/[a-z0-9]+(?:-[a-z0-9]+)*/",
                    route,
                ) or not isinstance(fields, dict):
                    errors.append(issue("FIXED_SEO_ROUTE_INVALID", str(route), "Invalid fixed-page SEO record"))
                    continue
                page_path = root / route.lstrip("/") / "index.html"
                if not page_path.is_file():
                    errors.append(issue("FIXED_SEO_ROUTE_MISSING", route, "Route absent in actual static build"))
                    continue
                page = Page()
                page.feed(page_path.read_text(encoding="utf-8"))
                slug = route.removeprefix("/guide/").removesuffix("/") if route.startswith("/guide/") else None
                section = published_sections.get(slug, {})
                for field in ("seo_title", "seo_description", "h1"):
                    value = section.get(field) or fields.get(field)
                    if value is None or not isinstance(value, str) or not value.strip():
                        continue
                    if field == "seo_title" and value not in page.title:
                        errors.append(issue("FIXED_SEO_TITLE_NOT_RENDERED", route, value[:80]))
                    if field == "seo_description" and not any(
                        value == m.get("content") for m in page.elements("meta")
                        if m.get("name") == "description"
                    ):
                        errors.append(issue("FIXED_SEO_DESCRIPTION_NOT_RENDERED", route, value[:80]))
                    if field == "h1" and not any(value == h for h in page.h1_texts):
                        errors.append(issue("FIXED_SEO_H1_NOT_RENDERED", route, value[:80]))
        for entry in obj["entries"]:
            checked_entries += 1
            slug = str(entry.get("slug", "(missing)"))
            for image in entry.get("media", []):
                src = image.get("src")
                if not isinstance(image.get("alt"), str) or not image["alt"].strip():
                    errors.append(issue("CMS_IMAGE_ALT", slug, f"Missing alt for {src}"))
                elif len(image["alt"]) > 125 or ALT_GENERIC.search(image["alt"]):
                    errors.append(issue("CMS_IMAGE_ALT_POLICY", slug, f"Noncompliant media alt for {src}"))
                if "long_description" in image and (
                    not isinstance(image["long_description"], str)
                    or len(image["long_description"]) > 3000
                ):
                    errors.append(issue("CMS_IMAGE_LONG_DESC", slug, f"Invalid extended description for {src}"))
                if not isinstance(src, str) or not src.startswith("/media/") or ".." in src:
                    errors.append(issue("CMS_IMAGE_PATH", slug, str(src)))
            translations = entry.get("translations", {})
            if "en" in translations:
                en = translations["en"]
                if not en.get("title", "").strip() or not en.get("body", "").strip():
                    errors.append(issue("EN_TRANSLATION_INCOMPLETE", slug, "EN title/body must be complete"))
            for document in entry.get("documents", []):
                href = document.get("href", "")
                checked_documents += 1
                match = DOC_NAME.fullmatch(href) if isinstance(href, str) else None
                if not match:
                    errors.append(issue("DOCUMENT_URL", slug, str(href)))
                    continue
                expected_hash = match.group(1)
                path = (root / href.lstrip("/")).resolve()
                if not path.is_relative_to(root) or not path.is_file():
                    errors.append(issue("DOCUMENT_NOT_FOUND", slug, href))
                    continue
                if hashlib.sha256(path.read_bytes()).hexdigest() != expected_hash:
                    errors.append(issue("DOCUMENT_CHECKSUM", slug, href))
                if document.get("format") != match.group(2):
                    errors.append(issue("DOCUMENT_FORMAT", slug, href))
                reviewed = document.get("accessibility_reviewed") is True
                note = document.get("accessibility_note")
                if not reviewed:
                    warnings.append(issue("DOCUMENT_UNREVIEWED", slug, href))
                    if note is not None:
                        errors.append(issue("DOCUMENT_PRIVATE_NOTE", slug, "Unreviewed note exposed"))
                elif not isinstance(note, str) or len(note.strip()) < 40:
                    errors.append(issue("DOCUMENT_NOTE_MISSING", slug, href))
                elif len(note) > 2000:
                    errors.append(issue("DOCUMENT_NOTE_LONG", slug, href))
                # Editor's self-check is NOT proof of PDF tags or PDF/UA.
                if match.group(2) == "pdf":
                    warnings.append(issue("PDF_UA_UNVERIFIED", slug, href))
    if strict_documents:
        errors.extend(w for w in warnings if w["code"] in
                      {"DOCUMENT_UNREVIEWED", "PDF_UA_UNVERIFIED"})
    counts = Counter(w["code"] for w in warnings)
    return {
        "mode": "STATIC_PREAWARD_AUTOMATED_NOT_GOST_CERTIFICATION",
        "summary": {
            "html_pages": len(pages), "cms_entries": checked_entries,
            "documents": checked_documents, "images_rendered": len(seen_images),
            "errors": len(errors), "warnings": len(warnings),
        },
        "errors": errors,
        "warnings": warnings,
        "warning_counts": dict(sorted(counts.items())),
        "manual_not_verified": [
            "Screen reader tests with real assistive technologies and users",
            "Keyboard-only use of all future ticketing/forms/interactive widgets",
            "200% zoom in native Safari and Chromium-GOST",
            "Contrast and semantics of brand assets after design approval",
            "All original museum documents: PDF-UA tags, reading order, selectable text and ГОСТ Р 70176-2022",
            "Authorized museum staff UAT, real content, translations, GDPR/152-FZ processing",
        ],
    }


def report_md(report: dict) -> str:
    summary = report["summary"]
    lines = [
        "# MusBread — automated static accessibility and content audit",
        "",
        "**Pre-award automated check, NOT ГОСТ/PDF-UA compliance or acceptance.**",
        "",
        "| Metric | Value |", "|---|---:|",
        *[f"| {key} | {value} |" for key, value in summary.items()],
        "",
        "## Errors",
        "",
    ]
    lines.extend(
        f"- [{x['code']}] {x['page']}: {x['detail']}" for x in report["errors"]
    )
    if not report["errors"]:
        lines.append("None in these automated checks.")
    lines.extend(["", "## Warnings", ""])
    lines.extend(
        f"- [{x['code']}] {x['page']}: {x['detail']}" for x in report["warnings"]
    )
    if not report["warnings"]:
        lines.append("None in these automated checks.")
    lines.extend(["", "## Cannot be verified by this script", ""])
    lines.extend("- " + x for x in report["manual_not_verified"])
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("build", type=Path)
    parser.add_argument("--snapshot", type=Path)
    parser.add_argument("--json", type=Path)
    parser.add_argument("--markdown", type=Path)
    parser.add_argument("--strict-documents", action="store_true")
    args = parser.parse_args()
    data = audit(args.build, args.snapshot, args.strict_documents)
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.markdown:
        args.markdown.parent.mkdir(parents=True, exist_ok=True)
        args.markdown.write_text(report_md(data), encoding="utf-8")
    print("STATIC ACCESSIBILITY/CONTENT:", data["summary"],
          "MODE=AUTOMATED_NOT_GOST_CERTIFICATION")
    if data["errors"]:
        print("ERROR SAMPLE:", data["errors"][:15])
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
