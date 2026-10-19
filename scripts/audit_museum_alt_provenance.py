#!/usr/bin/env python3
"""Source-linked alt review queue for historic museum photographs. No captions invented."""
from __future__ import annotations
import argparse
import collections
import csv
import json
from pathlib import Path
from audit_accessibility_content import Page, ALT_GENERIC

DATA_FILES = (
    "official-museum-photo-assets.json",
    "official-news-index-photo-assets.json",
    "official-deep-news-image-assets.json",
    "official-historical-exhibition-image-assets.json",
)
FIELDS = ("static_path", "rendered_alt", "render_occurrences", "page_count",
          "page_examples", "original_museum_source_url", "original_source_page",
          "original_museum_alt", "manual_review_reason")

def build_review(root: Path) -> tuple[list[dict[str,str|int]], dict]:
    root=root.resolve()
    out=root/"apps/web/out"
    data=root/"apps/web/src/data"
    if not (out/"index.html").is_file():
        raise FileNotFoundError("Requires complete local original museum static build")
    reverse: dict[str,list[dict]] = collections.defaultdict(list)
    for name in DATA_FILES:
        p=data/name
        if not p.is_file(): continue
        for url,meta in json.loads(p.read_text()).get("photos",{}).items():
            path=meta.get("path")
            if path: reverse[path].append({"original":url, "page":meta.get("source_page_url",""),
                                          "original_alt":meta.get("alt","")})
    occurrence: dict[tuple[str,str],set[str]]=collections.defaultdict(set)
    count: collections.Counter[tuple[str,str]]=collections.Counter()
    for html in sorted(out.rglob("*.html")):
        page=Page()
        page.feed(html.read_text(encoding="utf-8"))
        rel=html.relative_to(out).as_posix()
        for img in page.elements("img"):
            alt=img.get("alt","")
            if alt and (ALT_GENERIC.search(alt) or len(alt)>125):
                key=(img.get("src",""),alt)
                count[key]+=1
                occurrence[key].add(rel)
    rows=[]
    for (path,alt),n in sorted(count.items()):
        sources=reverse.get(path,[])
        if not sources:
            reason="NO_MATCHING_SOURCE_ASSET__REVIEW_REQUIRED"
        elif len(alt)>125:
            reason="OVERLONG_ALT__VISUAL_REVIEW_REQUIRED"
        elif "фотографи" in alt.lower() or "фото " in alt.lower():
            reason="NUMBERED_OR_GENERIC_PHOTO_LABEL__VISUAL_REVIEW_REQUIRED"
        else:
            reason="POSSIBLE_FALSE_POSITIVE_OR_GENERIC_LABEL__REVIEW_REQUIRED"
        rows.append({"static_path":path,"rendered_alt":alt,
                     "render_occurrences":n,"page_count":len(occurrence[(path,alt)]),
                     "page_examples":"; ".join(sorted(occurrence[(path,alt)])[:4]),
                     "original_museum_source_url":"; ".join(sorted({s["original"] for s in sources})),
                     "original_source_page":"; ".join(sorted({s["page"] for s in sources if s["page"]})),
                     "original_museum_alt":"; ".join(sorted({s["original_alt"] for s in sources if s["original_alt"]})),
                     "manual_review_reason":reason})
    summary={"total_html_pages":len(list(out.rglob("*.html"))),
             "total_audit_occurrences":sum(count.values()),
             "unique_image_and_alt_pairs":len(rows),
             "unique_static_images":len({r["static_path"] for r in rows}),
             "affected_html_pages":len(set().union(*occurrence.values())) if occurrence else 0,
             "unlinked_source_pairs":sum(1 for r in rows if not r["original_museum_source_url"]),
             "source_alt_available_pairs":sum(1 for r in rows if r["original_museum_alt"])}
    return rows,summary

def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root",type=Path,default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output",type=Path,default=Path("docs/tz-audit/ORIGINAL_MUSEUM_PHOTO_ALT_REVIEW_20261019.csv"))
    args=parser.parse_args()
    rows,summary=build_review(args.root)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open("w",newline="",encoding="utf-8-sig") as f:
        wr=csv.DictWriter(f,fieldnames=FIELDS,lineterminator=chr(10))
        wr.writeheader()
        wr.writerows(rows)
    print("SOURCE_FIRST_ALT_REVIEW",json.dumps(summary,ensure_ascii=False,sort_keys=True))
    if summary["total_html_pages"] < 900 or summary["total_audit_occurrences"]==0:
        raise RuntimeError("Unexpected missing original pages or audit data")
if __name__ == "__main__":
    main()
