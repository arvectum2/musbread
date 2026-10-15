#!/usr/bin/env python3
"""Local static release packager with SHA256 verification and atomic rollback.

This simulates the *public* release boundary, not the final closed network
transfer. Never deploy directly to customer systems without signed approval.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import shutil
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def files_with_hashes(src: Path) -> dict[str, str]:
    result = {}
    for path in sorted(src.rglob("*")):
        if path.is_symlink():
            raise ValueError("Symlinks are not allowed inside public output")
        if path.is_file():
            result[path.relative_to(src).as_posix()] = digest(path)
    if "index.html" not in result:
        raise ValueError("Site export missing index.html")
    return result


def prepare(source: Path, snapshot: Path, manifest: Path, dest: Path) -> str:
    if not source.is_dir() or not snapshot.is_file() or not manifest.is_file():
        raise ValueError("Build the site and export CMS snapshot first")
    raw = json.loads(manifest.read_text(encoding="utf-8"))
    expected = raw["files"]["published.json"]["sha256"]
    if digest(snapshot) != expected:
        raise ValueError("Public data SHA256 does not match manifest")
    checksums = files_with_hashes(source)
    body = json.dumps(checksums, sort_keys=True, separators=(",", ":")).encode("utf-8")
    release_id = hashlib.sha256(body).hexdigest()[:16]
    releases = dest / "releases"
    releases.mkdir(parents=True, exist_ok=True)
    final = releases / release_id

    if final.is_dir():
        if files_with_hashes(final) != checksums:
            # The release contains its own manifest, so ignore it during comparison.
            actual = files_with_hashes(final)
            actual.pop("release-manifest.json", None)
            if actual != checksums:
                raise ValueError("Existing release files have changed")
    else:
        staging = Path(tempfile.mkdtemp(prefix=".release-", dir=releases))
        try:
            shutil.copytree(source, staging, dirs_exist_ok=True, symlinks=False)
            if files_with_hashes(staging) != checksums:
                raise ValueError("Checksum mismatch during release staging")
            # Manifest is intentionally separate from the content hash.
            (staging / "release-manifest.json").write_text(
                json.dumps({"release": release_id, "files": checksums}, sort_keys=True, indent=2) + "\n",
                encoding="utf-8",
            )
            staging.rename(final)
        finally:
            if staging.exists():
                shutil.rmtree(staging)

    current = dest / "current"
    if current.is_symlink() and current.resolve() != final.resolve():
        _swap_link(dest / "previous", current.readlink())
    _swap_link(current, Path("releases") / release_id)
    return release_id


def _swap_link(link: Path, target: Path) -> None:
    temporary = link.with_name("." + link.name + ".tmp")
    temporary.unlink(missing_ok=True)
    temporary.symlink_to(target)
    os.replace(temporary, link)


def rollback(dest: Path) -> str:
    previous = dest / "previous"
    current = dest / "current"
    if not previous.is_symlink() or not current.is_symlink():
        raise ValueError("No previous release available")
    old = previous.readlink()
    new = current.readlink()
    release = (dest / old).resolve()
    if not release.is_dir() or release.parent != (dest / "releases").resolve():
        raise ValueError("Invalid rollback target")
    _swap_link(current, old)
    _swap_link(previous, new)
    return release.name


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("deploy", "rollback", "verify"))
    parser.add_argument("--output", type=Path, default=ROOT / "apps/web/out")
    parser.add_argument("--dest", type=Path, default=ROOT / "deploy/local")
    args = parser.parse_args()
    try:
        if args.action == "deploy":
            version = prepare(args.output, ROOT / "apps/web/src/data/published.json",
                              ROOT / "apps/web/public/snapshot-manifest.json", args.dest)
            print("DEPLOYED " + version)
        elif args.action == "rollback":
            print("ROLLED BACK " + rollback(args.dest))
        else:
            current = args.dest / "current"
            if not current.is_symlink() or not current.resolve().is_dir():
                raise ValueError("No current release to verify")
            path = current.resolve()
            manifest = json.loads((path / "release-manifest.json").read_text())
            actual = files_with_hashes(path)
            actual.pop("release-manifest.json", None)
            if actual != manifest["files"]:
                raise ValueError("Deployed release checksums do not match")
            print("VERIFIED " + manifest["release"])
    except (ValueError, OSError, KeyError) as e:
        parser.exit(1, str(e) + "\n")


if __name__ == "__main__":
    main()
