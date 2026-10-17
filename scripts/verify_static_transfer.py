#!/usr/bin/env python3
"""Checksum inventory for an OFFLINE static release transfer (TZ-107).

The manifest MUST be obtained and authenticated independently of the data
transport. Bare SHA256 is not a digital signature and cannot resist a party
who can replace BOTH payload and its sidecar. No museum transport is implied.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

from release_site import files_with_hashes


def inventory(root: Path) -> dict[str, object]:
    hashes = files_with_hashes(root)
    canonical = json.dumps(hashes, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return {
        "schema_version": 1,
        "sha256_of_canonical_inventory": hashlib.sha256(canonical).hexdigest(),
        "files": hashes,
    }


def _separate(root: Path, manifest: Path) -> None:
    if manifest.is_symlink():
        raise ValueError("Out-of-band checksum manifest cannot be a symlink")
    if root.resolve() == manifest.resolve() or root.resolve() in manifest.resolve().parents:
        raise ValueError("Checksum manifest must be kept outside the transferable payload")


def make_manifest(root: Path, manifest: Path) -> dict:
    _separate(root, manifest)
    if manifest.exists() or manifest.is_symlink():
        raise ValueError("Never overwrite an existing trusted checksum sidecar")
    result = inventory(root)
    manifest.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation to avoid silently overwriting separately approved data.
    with manifest.open("x", encoding="utf-8") as out:
        json.dump(result, out, ensure_ascii=False, sort_keys=True, indent=2)
        out.write("\n")
    return result


def verify_manifest(root: Path, manifest: Path) -> dict:
    _separate(root, manifest)
    if not manifest.is_file():
        raise ValueError("Trusted checksum manifest is missing")
    try:
        declared = json.loads(manifest.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise ValueError("Invalid trusted manifest") from exc
    if not isinstance(declared, dict) or set(declared) != {
        "schema_version", "sha256_of_canonical_inventory", "files"
    } or declared["schema_version"] != 1 or not isinstance(declared["files"], dict):
        raise ValueError("Unexpected checksum manifest schema")
    actual = inventory(root)
    if actual != declared:
        raise ValueError("Transferred static payload checksum mismatch")
    return actual


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("make", "verify"))
    parser.add_argument("payload", type=Path, help="Completed Next.js static output")
    parser.add_argument("manifest", type=Path, help="Separate trusted checksum inventory")
    args = parser.parse_args()
    if args.action == "make":
        result = make_manifest(args.payload, args.manifest)
        print("SENDER_SHA256 " + str(result["sha256_of_canonical_inventory"]))
    else:
        result = verify_manifest(args.payload, args.manifest)
        print("RECEIVER_SHA256_VERIFIED " + str(result["sha256_of_canonical_inventory"])
              + " files=" + str(len(result["files"])))


if __name__ == "__main__":
    main()
