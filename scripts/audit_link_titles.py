#!/usr/bin/env python3
"""TZ-189 fail-closed census of visible href links in the ACTUAL static release.

Additional title is supplementary context, never a substitute for text/aria
names. This checks title presence (not the truthfulness of new editorial text).
"""
import argparse
from html.parser import HTMLParser
from pathlib import Path

class TitleParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links = 0
        self.missing = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() != "a":
            return
        values = dict(attrs)
        href = values.get("href") or ""
        if not href.strip():
            return
        self.links += 1
        title = values.get("title") or ""
        if not title.strip():
            self.missing.append(href[:150])

def audit(root:Path) ->dict:
    if not (root/"index.html").is_file():
        raise ValueError("Missing static export homepage")
    pages=sorted(root.rglob("*.html"))
    missing={}
    links=0
    for page in pages:
        parser=TitleParser()
        parser.feed(page.read_text(encoding="utf-8"))
        links+=parser.links
        if parser.missing:
            missing[str(page.relative_to(root))]=parser.missing
    return {"html_pages":len(pages),"links":links,
            "pages_missing_link_titles":len(missing),
            "missing_titles":missing}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("root",type=Path)
    args=parser.parse_args()
    report=audit(args.root)
    print("TZ-189 STATIC LINK TITLES:",{k:v for k,v in report.items() if k!="missing_titles"})
    if report["missing_titles"]:
        for path,links in list(report["missing_titles"].items())[:12]:
            print("MISSING",path,*links[:5])
        raise SystemExit(1)

if __name__=="__main__":
    main()
