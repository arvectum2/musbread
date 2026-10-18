#!/usr/bin/env python3
"""Generate a strict script-hash Content Security Policy for a static Next.js build.

Static HTML lacks request-time nonces. Every inline script emitted by Next.js
is hashed from the exact UTF-8 bytes and authorized explicitly; no unsafe-inline
JavaScript, no unsafe-eval and no external JavaScript origins are necessary.
The policy must be regenerated, installed and reloaded with EACH release.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
from html.parser import HTMLParser
from pathlib import Path


class InlineScriptCollector(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.inside = False
        self.chunks: list[str] = []
        self.scripts: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag != "script":
            return
        attributes = dict(attrs)
        self.inside = attributes.get("src") is None
        self.chunks = []

    def handle_data(self, data):
        if self.inside:
            self.chunks.append(data)

    def handle_entityref(self, name):
        if self.inside:
            self.chunks.append("&" + name + ";")

    def handle_charref(self, name):
        if self.inside:
            self.chunks.append("&#" + name + ";")

    def handle_endtag(self, tag):
        if tag == "script":
            if self.inside:
                self.scripts.append("".join(self.chunks))
            self.inside = False


def make_csp(build: Path) -> str:
    if not (build / "index.html").is_file():
        raise ValueError("Static site must be built before CSP generation")
    all_html = sorted(build.rglob("*.html"))
    hashes: set[str] = set()
    for file in all_html:
        parser = InlineScriptCollector()
        parser.feed(file.read_text(encoding="utf-8"))
        for script in parser.scripts:
            digest = base64.b64encode(hashlib.sha256(script.encode("utf-8")).digest()).decode("ascii")
            hashes.add("'sha256-" + digest + "'")
    if not hashes:
        raise ValueError("Refusing CSP without any inline script hashes: verify Next.js build")
    directives = [
        "default-src 'none'",
        "base-uri 'none'",
        "object-src 'none'",
        "frame-ancestors 'none'",
        "form-action 'self'",
        "script-src 'self' " + " ".join(sorted(hashes)),
        "script-src-attr 'none'",
        # Next.js and the current site need inline style properties. JS remains
        # strictly hashed; further style hardening is a separate task.
        "style-src 'self' 'unsafe-inline'",
        "img-src 'self' data:",
        "font-src 'self' data:",
        "connect-src 'self'",
        # A specific pre-verified museum-owned Yandex constructor may load
        # only after the visitor explicitly activates its iframe.
        # Never open script-src / connect-src / img-src to Yandex at top level.
        "frame-src https://yandex.ru https://vk.com https://vkvideo.ru",
        "worker-src 'self'",
        "manifest-src 'self'",
    ]
    return "; ".join(directives)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("static_output", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    csp = make_csp(args.static_output)
    if '"' in csp or "\r" in csp or "\n" in csp:
        raise ValueError("CSP contains unsafe Nginx header characters")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        '# Automatically generated from THIS EXACT static Next.js build.\n'
        '# Install together with this build; reload Nginx; regenerate after rollback.\n'
        'add_header Content-Security-Policy "' + csp + '" always;\n',
        encoding="utf-8",
    )
    print("CSP GENERATED for", len(list(args.static_output.rglob("*.html"))),
          "HTML pages, policy bytes:", len(csp.encode()))


if __name__ == "__main__":
    main()
