#!/usr/bin/env python3
"""Build a deterministic, integrity-verifiable read-only site snapshot.

Pre-award fixture publisher; Laravel CMS will replace the fixture input.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SAFE_SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def encode(data: object) -> bytes:
    return (json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def build(source: Path, snapshot: Path, manifest: Path, check: bool = False) -> None:
    data = json.loads(source.read_text(encoding="utf-8"))
    if data.get("schema_version") != 1 or not isinstance(data.get("events"), list):
        raise ValueError("Unsupported content schema")
    if not isinstance(data.get("site"), dict):
        raise ValueError("Site metadata is required")
    seen = set()
    for event in data["events"]:
        if not isinstance(event, dict):
            raise ValueError("Each event must be an object")
        for field in ("slug", "title", "category", "date", "excerpt", "body"):
            if not isinstance(event.get(field), str) or not event[field].strip():
                raise ValueError(f"Missing or empty event field: {field}")
        slug = event["slug"]
        if not SAFE_SLUG.fullmatch(slug) or slug in seen:
            raise ValueError("Slug must be unique and URL-safe")
        seen.add(slug)
    allowed_types = {"page", "news", "excursion", "exhibition", "document"}
    entries = data.setdefault("entries", [])
    if not isinstance(entries, list):
        raise ValueError("Content entries must be an array")
    entry_slugs = set()
    for entry in entries:
        if not isinstance(entry, dict) or entry.get("type") not in allowed_types:
            raise ValueError("Unknown museum content type")
        slug = entry.get("slug")
        if not isinstance(slug, str) or not SAFE_SLUG.fullmatch(slug) or slug in entry_slugs:
            raise ValueError("Content slug must be unique and URL safe")
        entry_slugs.add(slug)
        for field in ("title", "body"):
            if not isinstance(entry.get(field), str) or not entry[field].strip():
                raise ValueError("Missing title/body for museum entry")
    entries.sort(key=lambda e: (e["type"], e.get("sort_order", 0), e["slug"]))
    # Normalize order for reproducible output and auditability.
    data["events"].sort(key=lambda x: (x["date"], x["slug"]))
    payload = encode(data)
    digest = hashlib.sha256(payload).hexdigest()
    audit = {"schema_version": 1, "files": {"published.json": {"sha256": digest, "bytes": len(payload)}}, "event_count": len(data["events"]), "entry_count": len(entries)}
    audit_bytes = encode(audit)
    if check:
        if snapshot.read_bytes() != payload or manifest.read_bytes() != audit_bytes:
            raise SystemExit("Snapshot differs from fixtures; run python3 scripts/publish_snapshot.py")
        print("OK snapshot sha256=" + digest)
        return
    snapshot.parent.mkdir(parents=True, exist_ok=True)
    manifest.parent.mkdir(parents=True, exist_ok=True)
    for path, content in ((snapshot, payload), (manifest, audit_bytes)):
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_bytes(content)
        tmp.replace(path)
    print("Published fixture snapshot: " + digest)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    build(ROOT / "fixtures/content.json", ROOT / "apps/web/src/data/published.json",
          ROOT / "apps/web/public/snapshot-manifest.json", args.check)


if __name__ == "__main__":
    main()
