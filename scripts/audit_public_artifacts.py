#!/usr/bin/env python3
"""Fail the public release if private assets or known secret patterns leak.

Pre-award static build check, *not* a substitute for penetration testing.
"""
import argparse
import hashlib
import json
import re

VALID_DOCUMENT = re.compile(r"^documents/[a-f0-9]{64}\.(?:pdf|docx|xlsx)$")
from pathlib import Path

ALLOWED = {".html", ".js", ".css", ".txt", ".json", ".ico", ".svg",
           ".webp", ".png", ".jpg", ".jpeg", ".xml", ".pdf", ".docx", ".xlsx", ".woff", ".woff2"}
FORBIDDEN_DIRS = {"admin", "api", "storage", "vendor", "database", "node_modules", ".git"}
FORBIDDEN_NAMES = {
    "artisan", "composer.json", "composer.lock", "package-lock.json",
    "phpunit.xml", ".htaccess", "id_rsa", "id_ed25519", "credentials.json",
}
SECRET_MARKERS = [
    b"-----BEGIN PRIVATE KEY-----", b"-----BEGIN OPENSSH PRIVATE KEY-----",
    b"DB_PASSWORD=", b"APP_KEY=base64:", b"MUSBREAD_E2E_PASSWORD=",
]
TEXT_EXT = {".html", ".js", ".css", ".json", ".txt", ".xml", ".svg"}


def audit(root: Path) -> dict[str, int]:
    if not root.is_dir() or root.is_symlink() or not (root / "index.html").is_file():
        raise ValueError("A generated static site with index.html is required")
    count = 0
    for path in root.rglob("*"):
        if path.is_symlink():
            raise ValueError("Symlink in public export: " + str(path))
        if not path.is_file():
            continue
        parts = path.relative_to(root).parts
        if any(part.startswith(".env") or part in FORBIDDEN_DIRS for part in parts):
            raise ValueError("Private directory or env file in public export: " + str(path))
        if path.name in FORBIDDEN_NAMES or path.suffix.lower() not in ALLOWED:
            raise ValueError("Unsafe public file: " + str(path))
        if path.suffix.lower() in TEXT_EXT:
            content = path.read_bytes()
            if any(secret in content for secret in SECRET_MARKERS):
                raise ValueError("Secret-like content in public export: " + str(path))
        count += 1

    # Public static assets must independently match the CMS export manifest.
    manifest = root / "snapshot-manifest.json"
    if manifest.is_file():
        data = json.loads(manifest.read_text(encoding="utf-8"))
        for name, meta in data["files"].items():
            if name == "published.json":
                continue  # JSON is compiled into HTML/JS, not shipped as a standalone file.
            valid_media = name.startswith("media/") and "/" not in name[6:] and name.endswith(".webp")
            if not valid_media and not VALID_DOCUMENT.fullmatch(name):
                raise ValueError("Unexpected path in CMS manifest: " + name)
            media = root / name
            if not media.is_file() or media.is_symlink():
                raise ValueError("Missing published media: " + name)
            if media.stat().st_size != meta["bytes"] or hashlib.sha256(media.read_bytes()).hexdigest() != meta["sha256"]:
                raise ValueError("Public media integrity check failed: " + name)
    return {"files_checked": count}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    print("PUBLIC ARTIFACT AUDIT: " + json.dumps(audit(args.directory)))


if __name__ == "__main__":
    main()
