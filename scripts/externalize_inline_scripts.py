#!/usr/bin/env python3
"""Externalize ONLY executable Next.js inline JS into immutable same-origin SRI assets.

Run AFTER Next static export and legacy aliases, BEFORE computing CSP/release.
Original HTML JS bytes and script execution order are preserved. No CMS data,
network access, JS inline exceptions or third-party hosting.
"""
from __future__ import annotations
import argparse
import base64
import hashlib
import json
import re
from html.parser import HTMLParser
from pathlib import Path

ASSET_REL = "_next/static/musbread-inline"
MANIFEST_REL = ASSET_REL + "/manifest.json"
SCRIPT_RE = re.compile(r"(<script\b[^>]*>)(.*?)</script\s*>", re.I | re.S)
NAME_RE = re.compile(r"[a-f0-9]{64}\.js\Z")


class Tag(HTMLParser):
    def __init__(self):
        super().__init__()
        self.attributes: dict[str, str | None] = {}

    def handle_starttag(self, tag, attrs):
        if tag == "script":
            self.attributes = dict(attrs)


def executable(start: str) -> tuple[bool, dict[str, str | None]]:
    parser = Tag()
    parser.feed(start)
    attrs = parser.attributes
    script_type = (attrs.get("type") or "").strip().lower()
    return ("src" not in attrs and script_type in ("", "text/javascript",
            "application/javascript", "module")), attrs


def asset_for(body: str) -> tuple[str, bytes, str]:
    raw = body.encode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()
    integrity = "sha384-" + base64.b64encode(hashlib.sha384(raw).digest()).decode("ascii")
    return digest + ".js", raw, integrity


def merge_adjacent_flight_payloads(html: str) -> str:
    """Batch only consecutive React Flight pushes; do not move other scripts.

    Next.js emits hundreds of adjacent self.__next_f.push(...) tags for long
    pages. They update one ordered array and can execute sequentially from one
    SRI-protected file, saving hundreds of extra requests without touching
    bootstrap scripts, DOM markup, or script ordering.
    """
    matches = list(SCRIPT_RE.finditer(html))
    parts: list[str] = []
    cursor = 0
    i = 0

    def is_flight(m: re.Match[str]) -> bool:
        allowed, attrs = executable(m.group(1))
        return allowed and not attrs and m.group(2).startswith("self.__next_f.push(")

    while i < len(matches):
        first = matches[i]
        if not is_flight(first):
            i += 1
            continue
        j = i + 1
        while (j < len(matches) and is_flight(matches[j])
               and not html[matches[j - 1].end():matches[j].start()].strip()):
            j += 1
        if j > i + 1:
            payload = ";\n".join(m.group(2) for m in matches[i:j])
            parts.append(html[cursor:first.start()])
            parts.append(first.group(1) + payload + "</script>")
            cursor = matches[j - 1].end()
        i = j
    parts.append(html[cursor:])
    return "".join(parts)


def transform(html: str) -> tuple[str, dict[str, bytes], int]:
    assets: dict[str, bytes] = {}
    count = 0

    def replace(match: re.Match[str]) -> str:
        nonlocal count
        start, body = match.group(1), match.group(2)
        can_run, attrs = executable(start)
        if not can_run or not body:
            return match.group(0)
        if any(k in attrs for k in ("integrity", "crossorigin", "nonce")):
            raise ValueError("Inline script unexpectedly declares integrity/crossorigin/nonce")
        filename, raw, integrity = asset_for(body)
        assets[filename] = raw
        count += 1
        return (start[:-1] + f' src="/{ASSET_REL}/{filename}"'
                f' integrity="{integrity}" crossorigin="anonymous"></script>')

    result = SCRIPT_RE.sub(replace, merge_adjacent_flight_payloads(html))
    # Unprocessed executable JS would be blocked by the strictly enforced CSP.
    for match in SCRIPT_RE.finditer(result):
        can_run, _ = executable(match.group(1))
        if can_run and match.group(2).strip():
            raise ValueError("Executable inline JavaScript remains in static page")
    return result, assets, count


def externalize(out: Path, verify_only: bool = False) -> dict:
    if not out.is_dir() or out.is_symlink() or not (out / "index.html").is_file():
        raise ValueError("Missing genuine static export root")
    if not (out / "_next/static").is_dir():
        raise ValueError("Next.js static chunks must exist before externalization")
    pages = sorted(out.rglob("*.html"))
    assets: dict[str, bytes] = {}
    altered: dict[Path, str] = {}
    count = 0
    for page in pages:
        if page.is_symlink():
            raise ValueError("Symlink HTML is forbidden: " + str(page))
        original = page.read_text(encoding="utf-8")
        processed, scripts, total = transform(original)
        count += total
        for name, data in scripts.items():
            if name in assets and assets[name] != data:
                raise ValueError("SHA-256 content-address collision")
            assets[name] = data
        if processed != original:
            altered[page] = processed

    target = out / ASSET_REL
    manifest = target / "manifest.json"
    if verify_only:
        if not manifest.is_file() or manifest.is_symlink():
            raise ValueError("Executable JS SRI manifest missing: build not externalized")
        recorded = json.loads(manifest.read_text(encoding="utf-8"))
        if recorded.get("schema") != 1:
            raise ValueError("Invalid externalized JS manifest")
        built_pages = recorded.get("html_pages")
        if built_pages != len(pages):
            # Original museum news archive pages are restored AFTER Next
            # postbuild. No other late-generated HTML pages are allowed.
            extra = [p for p in pages if p.relative_to(out).parts[0] == "__museum_legacy_pager"]
            if not (len(extra) == 27 and built_pages == len(pages) - 27):
                raise ValueError("Stale/invalid externalized JS manifest")
        expected_assets = recorded.get("assets", {})
        if not isinstance(expected_assets, dict) or not expected_assets:
            raise ValueError("Empty SRI asset manifest")
        if count or altered:
            raise ValueError("Unexternalized inline JS remains in static export")
        real_assets = sorted(p.name for p in target.iterdir() if p.is_file() and p.name.endswith(".js"))
        if sorted(expected_assets) != real_assets:
            raise ValueError("Missing/orphaned external JS assets")
        for name, info in expected_assets.items():
            if not NAME_RE.fullmatch(name):
                raise ValueError("Invalid SRI filename")
            raw = (target / name).read_bytes()
            if (len(raw) != info.get("bytes") or
                    hashlib.sha256(raw).hexdigest() != name.removesuffix(".js")):
                raise ValueError("Modified externalized Next.js script: " + name)
        referenced: set[str] = set()
        references = 0
        for page in pages:
            source = page.read_text(encoding="utf-8")
            # Immutable external scripts must use the generated hash/SRI pair.
            for tag in re.finditer(r"<script\b[^>]*>", source, re.I):
                parsed = Tag()
                parsed.feed(tag.group())
                attrs = parsed.attributes
                uri = attrs.get("src") or ""
                if not uri.startswith(f"/{ASSET_REL}/"):
                    continue
                name = uri.rsplit("/", 1)[-1]
                if name not in expected_assets:
                    raise ValueError("Unknown external script referenced by HTML")
                referenced.add(name)
                references += 1
                raw = (target / name).read_bytes()
                expected_integrity = "sha384-" + base64.b64encode(hashlib.sha384(raw).digest()).decode()
                if attrs.get("integrity") != expected_integrity or attrs.get("crossorigin") != "anonymous":
                    raise ValueError("External script SRI missing/mismatched")
        if referenced != set(expected_assets) or references != recorded.get("externalized_occurrences"):
            raise ValueError("Externalized SRI manifest reference count or coverage mismatch")
        return {"html_pages": len(pages), "assets": len(expected_assets), "remaining_inline": 0}

    if manifest.exists():
        # Regenerating in place is only safe for a newly-built export. An
        # existing externalized release must pass integrity verification first.
        if not altered:
            return externalize(out, verify_only=True)
        raise ValueError("Existing manifest with unprocessed HTML: rebuild from clean export")
    target.mkdir(parents=True, exist_ok=True)
    for name, raw in assets.items():
        dst = target / name
        if dst.exists() and dst.read_bytes() != raw:
            raise ValueError("Externalized content-addressed asset altered")
        dst.write_bytes(raw)
    for page, html in altered.items():
        page.write_text(html, encoding="utf-8")
    metadata = {"schema": 1, "html_pages": len(pages),
                "externalized_occurrences": count,
                "assets": {name: {"bytes": len(data)} for name, data in sorted(assets.items())}}
    manifest.write_text(json.dumps(metadata, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return externalize(out, verify_only=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("static_export", type=Path)
    ap.add_argument("--verify-only", action="store_true")
    args = ap.parse_args()
    result = externalize(args.static_export, verify_only=args.verify_only)
    print("MUSBREAD_EXTERNAL_SRI_PASS", result, flush=True)
