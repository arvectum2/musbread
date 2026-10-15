#!/usr/bin/env python3
"""Local static release packager with SHA256 verification and atomic rollback.

This simulates the *public* release boundary, not the final closed network
transfer. Never deploy directly to customer systems without signed approval.
"""
from __future__ import annotations
import argparse
import fcntl
from contextlib import contextmanager
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


@contextmanager
def release_lock(dest: Path):
    """Serialize deploy/rollback/verify; no two releases may switch current together."""
    dest.mkdir(parents=True, exist_ok=True)
    if dest.is_symlink():
        raise ValueError("Release destination must not be a symlink")
    path = dest / ".release.lock"
    if path.is_symlink():
        raise ValueError("Release lock must not be a symlink")
    with path.open("a+b") as lockfile:
        fcntl.flock(lockfile.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lockfile.fileno(), fcntl.LOCK_UN)


def validate_release(path: Path) -> str:
    """Reject tampered or incomplete immutable releases before they become public."""
    if not path.is_dir() or path.is_symlink():
        raise ValueError("Release directory missing or unsafe")
    manifest_path = path / "release-manifest.json"
    if not manifest_path.is_file() or manifest_path.is_symlink():
        raise ValueError("Release manifest missing")
    info = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected = info["files"]
    if not isinstance(expected, dict) or "index.html" not in expected:
        raise ValueError("Release manifest has an invalid file inventory")
    actual = files_with_hashes(path)
    actual.pop("release-manifest.json", None)
    if actual != expected:
        raise ValueError("Release checksum mismatch")
    canonical = json.dumps(expected, sort_keys=True, separators=(",", ":")).encode("utf-8")
    release_id = hashlib.sha256(canonical).hexdigest()[:16]
    if info.get("release") != release_id or path.name != release_id:
        raise ValueError("Release identity mismatch")
    return release_id


def prepare(source: Path, snapshot: Path, manifest: Path, dest: Path) -> str:
    with release_lock(dest):
        return _prepare_unlocked(source, snapshot, manifest, dest)


def _prepare_unlocked(source: Path, snapshot: Path, manifest: Path, dest: Path) -> str:
    if not source.is_dir() or not snapshot.is_file() or not manifest.is_file():
        raise ValueError("Build the site and export CMS snapshot first")
    raw = json.loads(manifest.read_text(encoding="utf-8"))
    expected = raw["files"]["published.json"]["sha256"]
    if digest(snapshot) != expected:
        raise ValueError("Public data SHA256 does not match manifest")
    # Independently authenticate each media file announced by the CMS exporter.
    # Missing or replaced static assets invalidate the entire release.
    for name, info in raw["files"].items():
        if name == "published.json":
            continue
        if not name.startswith("media/") or "/" in name[len("media/"):] or not name.endswith(".webp"):
            raise ValueError("Unexpected media path in publication manifest")
        public_file = source / name
        if not public_file.is_file() or public_file.is_symlink():
            raise ValueError("Missing or unsafe exported media file: " + name)
        if public_file.stat().st_size != info["bytes"] or digest(public_file) != info["sha256"]:
            raise ValueError("Exported media checksum mismatch: " + name)
    checksums = files_with_hashes(source)
    body = json.dumps(checksums, sort_keys=True, separators=(",", ":")).encode("utf-8")
    release_id = hashlib.sha256(body).hexdigest()[:16]
    releases = dest / "releases"
    releases.mkdir(parents=True, exist_ok=True)
    final = releases / release_id

    if final.exists() or final.is_symlink():
        validate_release(final)
        existing = files_with_hashes(final)
        existing.pop("release-manifest.json", None)
        if existing != checksums:
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
    with release_lock(dest):
        return _rollback_unlocked(dest)


def _rollback_unlocked(dest: Path) -> str:
    previous = dest / "previous"
    current = dest / "current"
    if not previous.is_symlink() or not current.is_symlink():
        raise ValueError("No previous release available")
    old = previous.readlink()
    new = current.readlink()
    release = (dest / old).resolve()
    if not release.is_dir() or release.parent != (dest / "releases").resolve():
        raise ValueError("Invalid rollback target")
    validate_release(release)
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
            with release_lock(args.dest):
                current = args.dest / "current"
                if not current.is_symlink() or not current.resolve().is_dir():
                    raise ValueError("No current release to verify")
                path = current.resolve()
                if path.parent != (args.dest / "releases").resolve():
                    raise ValueError("Current release target outside release directory")
                print("VERIFIED " + validate_release(path))
    except (ValueError, OSError, KeyError) as e:
        parser.exit(1, str(e) + "\n")


if __name__ == "__main__":
    main()
