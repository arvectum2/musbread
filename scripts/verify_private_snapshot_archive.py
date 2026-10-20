#!/usr/bin/env python3
"""Offline read-only verification of MusBread's opt-in private export archives.

Does not import Laravel or connect to a database/production server.
For adversarial checks, use --expected-receipt-sha256 from a separately
retained value in CMS. A self-contained receipt is NOT a trusted signature.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

HASH = re.compile(r"[0-9a-f]{64}\Z")
ASSET = re.compile(r"(?:media/[0-9a-f]{64}\.webp|documents/[0-9a-f]{64}\.(?:pdf|docx|xlsx))\Z")
IDENTITY = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")


class ArchiveInvalid(ValueError):
    pass


def unique_object(pairs):
    values = {}
    for k, v in pairs:
        if k in values:
            raise ArchiveInvalid("duplicate JSON key")
        values[k] = v
    return values


def parse(blob: bytes) -> dict:
    try:
        data = json.loads(blob, object_pairs_hook=unique_object)
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        raise ArchiveInvalid("invalid archive JSON") from e
    if not isinstance(data, dict):
        raise ArchiveInvalid("archive JSON must be an object")
    return data


def canonical(row: dict) -> bytes:
    # Same sorted-key, UTF-8, compact and terminating LF encoding as the
    # MuseumSnapshotSerializer's public schema-v1 object rows.
    return (json.dumps(row, sort_keys=True, ensure_ascii=False,
                       separators=(",", ":")) + "\n").encode("utf-8")


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def regular(root: Path, name: str) -> bytes:
    if name != "published.json" and name != "snapshot-manifest.json" and \
       name != "archive-receipt.json" and not ASSET.fullmatch(name):
        raise ArchiveInvalid("unrecognized or unsafe archive path")
    target = root.joinpath(*name.split("/"))
    if target.is_symlink() or any(parent.is_symlink() for parent in target.parents if parent != root):
        raise ArchiveInvalid("archive file or directory is a symlink")
    if not target.is_file():
        raise ArchiveInvalid("archive file missing")
    return target.read_bytes()


def verify(directory: Path, *, expected_receipt_sha256: str | None = None) -> dict:
    if directory.is_symlink() or not directory.is_dir():
        raise ArchiveInvalid("archive directory is missing or symlinked")
    root = directory.resolve(strict=True)
    if expected_receipt_sha256 is not None and not HASH.fullmatch(expected_receipt_sha256):
        raise ArchiveInvalid("invalid external receipt hash")
    receipt_bytes = regular(root, "archive-receipt.json")
    receipt_hash = digest(receipt_bytes)
    if expected_receipt_sha256 is not None and receipt_hash != expected_receipt_sha256:
        raise ArchiveInvalid("receipt bytes differ from separately retained digest")
    receipt = parse(receipt_bytes)
    if set(receipt) != {"schema_version", "publication_run_id",
                        "snapshot_sha256", "manifest_sha256", "files", "proofs"} or \
       receipt["schema_version"] != 1 or type(receipt["publication_run_id"]) is not int or \
       receipt["publication_run_id"] <= 0:
        raise ArchiveInvalid("invalid receipt schema")
    expected_name = ("run-" + str(receipt["publication_run_id"]) + "-"
                     + receipt["snapshot_sha256"] + "-" + receipt["manifest_sha256"])
    if root.name != expected_name or not HASH.fullmatch(receipt["snapshot_sha256"]) or \
       not HASH.fullmatch(receipt["manifest_sha256"]):
        raise ArchiveInvalid("archive directory identity does not match receipt")

    files = receipt["files"]
    if not isinstance(files, dict) or not 2 <= len(files) <= 5002 or \
       set(("published.json", "snapshot-manifest.json")) - set(files):
        raise ArchiveInvalid("invalid archive file inventory")
    encountered = {"archive-receipt.json"}
    blobs = {}
    for name, meta in files.items():
        if name not in ("published.json", "snapshot-manifest.json") and \
           not ASSET.fullmatch(name):
            raise ArchiveInvalid("undeclared or dangerous archive filename")
        if not isinstance(meta, dict) or set(meta) != {"bytes", "sha256"} or \
           type(meta["bytes"]) is not int or meta["bytes"] < 0 or \
           not isinstance(meta["sha256"], str) or not HASH.fullmatch(meta["sha256"]):
            raise ArchiveInvalid("invalid file metadata")
        blob = regular(root, name)
        if len(blob) != meta["bytes"] or digest(blob) != meta["sha256"]:
            raise ArchiveInvalid("file digest or byte count differs from receipt: " + name)
        blobs[name] = blob
        encountered.add(name)

    for obj in root.rglob("*"):
        if obj.is_symlink():
            raise ArchiveInvalid("unexpected archive symlink")
        if obj.is_file():
            relative = obj.relative_to(root).as_posix()
            if relative not in encountered:
                raise ArchiveInvalid("unlisted archive file: " + relative)
        elif obj.is_dir() and obj.relative_to(root).as_posix() not in ("media", "documents"):
            raise ArchiveInvalid("unexpected archive directory")
    if blobs["published.json"] and digest(blobs["published.json"]) != receipt["snapshot_sha256"]:
        raise ArchiveInvalid("snapshot hash differs")
    if digest(blobs["snapshot-manifest.json"]) != receipt["manifest_sha256"]:
        raise ArchiveInvalid("manifest hash differs")
    manifest = parse(blobs["snapshot-manifest.json"])
    snapshot = parse(blobs["published.json"])
    if manifest.get("schema_version") != 1 or snapshot.get("schema_version") != 1:
        raise ArchiveInvalid("incorrect snapshot or manifest schema")
    if not isinstance(manifest.get("files"), dict) or \
       manifest["files"] != {k: v for k, v in files.items() if k != "snapshot-manifest.json"}:
        raise ArchiveInvalid("archive inventory disagrees with original manifest")

    records = {}
    referenced_assets: set[str] = set()
    for kind, key in (("entry", "entries"), ("event", "events"), ("section", "sections")):
        items = snapshot.get(key, [] if kind == "section" else None)
        if not isinstance(items, list):
            raise ArchiveInvalid("subject collection is not a list")
        for row in items:
            if not isinstance(row, dict):
                raise ArchiveInvalid("subject is not a JSON object")
            slug = row.get("slug")
            if not isinstance(slug, str) or not IDENTITY.fullmatch(slug):
                raise ArchiveInvalid("unsafe archive subject identity")
            identity = slug
            if kind == "entry":
                type_name = row.get("type")
                if type_name not in ("page", "news", "excursion", "exhibition", "document"):
                    raise ArchiveInvalid("invalid public entry type")
                identity = type_name + ":" + slug
            name = (kind, identity)
            if name in records:
                raise ArchiveInvalid("duplicate archive subject identity")
            records[name] = digest(canonical(row))
            if kind == "entry":
                for media in row.get("media", []):
                    referenced_assets.add(media["src"].lstrip("/"))
                for document in row.get("documents", []):
                    referenced_assets.add(document["href"].lstrip("/"))
            elif kind == "event" and row.get("cover_image"):
                referenced_assets.add(row["cover_image"]["src"].lstrip("/"))
    if not isinstance(manifest.get("entry_count"), int) or \
       len(snapshot["entries"]) != manifest["entry_count"] or \
       not isinstance(manifest.get("event_count"), int) or \
       len(snapshot["events"]) != manifest["event_count"] or \
       (("sections" in snapshot) != ("section_count" in manifest)) or \
       ("sections" in snapshot and len(snapshot["sections"]) != manifest["section_count"]):
        raise ArchiveInvalid("manifest object counts differ")
    manifest_assets = set(files) - {"published.json", "snapshot-manifest.json"}
    if manifest_assets != referenced_assets:
        raise ArchiveInvalid("snapshot asset links do not match archive inventory")
    for asset in manifest_assets:
        expected = asset.split("/")[-1].split(".")[0]
        if files[asset]["sha256"] != expected:
            raise ArchiveInvalid("content-addressed asset name differs from hash")

    proofs = receipt["proofs"]
    if not isinstance(proofs, list) or len(proofs) != len(records):
        raise ArchiveInvalid("proof count differs from exported subjects")
    seen = set()
    for item in proofs:
        if not isinstance(item, dict) or set(item) != {
            "kind", "identity", "subject_id", "approval_id",
            "revision_sha256", "export_record_sha256",
        } or type(item["subject_id"]) is not int or item["subject_id"] <= 0 or \
            type(item["approval_id"]) is not int or item["approval_id"] <= 0 or \
            not isinstance(item["revision_sha256"], str) or \
            not HASH.fullmatch(item["revision_sha256"]):
            raise ArchiveInvalid("invalid proof metadata")
        identity = (item["kind"], item["identity"])
        if identity in seen or identity not in records or \
           item["export_record_sha256"] != records[identity]:
            raise ArchiveInvalid("proof row does not match canonical archive JSON")
        seen.add(identity)
    return {"receipt_sha256": receipt_hash, "snapshot_sha256": receipt["snapshot_sha256"],
            "manifest_sha256": receipt["manifest_sha256"], "files": len(files),
            "approved_subjects": len(proofs), "run_id": receipt["publication_run_id"],
            "externally_anchored": expected_receipt_sha256 is not None}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path, help="Existing private archive directory")
    parser.add_argument("--expected-receipt-sha256",
                        help="Separately recorded receipt SHA-256 (e.g. CMS publication_runs)")
    args = parser.parse_args()
    try:
        result = verify(args.directory, expected_receipt_sha256=args.expected_receipt_sha256)
    except (ArchiveInvalid, OSError, KeyError, TypeError, ValueError) as error:
        print("PRIVATE_ARCHIVE_FAIL:", str(error))
        return 1
    print("PRIVATE_ARCHIVE_PASS", json.dumps(result, ensure_ascii=False, sort_keys=True))
    if not result["externally_anchored"]:
        print("WARNING: self-contained integrity only; provide an external receipt SHA for authenticity")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
