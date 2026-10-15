#!/usr/bin/env python3
"""Build/verify a reproducible PRE-AWARD handoff demonstration from Git HEAD.

No .env credentials, local databases, npm/vendor trees or generated build output.
No legal rights are claimed or transferred by this tool.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import io
import json
import re
import subprocess
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

ROOTS = {"apps", "docs", "fixtures", "infra", "scripts", "tests", ".github"}
ROOT_FILES = {"README.md", ".gitignore"}
OMIT_NAMES = {"AGENTS.md", "CLAUDE.md", ".npmrc", ".DS_Store"}
OMIT_EXT = {".sqlite", ".db", ".pem", ".key", ".p12", ".pfx"}
EXTRA = {"README_FIRST.md", "MANIFEST.json", "STATUS.json", "INVENTORY.csv", "SHA256SUMS"}
REQUIRED = (".ai", ".eps", ".svg", ".psd", ".tiff", ".ppt", ".pptx")
ZIP_TIME = (2020, 1, 1, 0, 0, 0)
MAX_SIZE = 24_000_000
MAX_TOTAL = 192_000_000
TOKEN = [re.compile(x) for x in (
    rb"(?m)^-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----[ \t]*$",
    rb"ghp_[A-Za-z0-9]{30,}",
    rb"github_pat_[A-Za-z0-9_]{30,}",
    rb"glpat-[A-Za-z0-9_-]{20,}",
)]

@dataclass(frozen=True)
class Item:
    path: str
    data: bytes

def checksum(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def jsonbytes(data: object) -> bytes:
    return (json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()

def source_allowed(name: str) -> bool:
    p = PurePosixPath(name)
    if not name or "\x00" in name or "\\" in name or p.is_absolute() or ".." in p.parts:
        return False
    if name in ROOT_FILES:
        return True
    if p.parts[0] not in ROOTS or len(p.parts) < 2:
        return False
    if p.parts[0] == ".github" and p.parts[1] != "workflows":
        return False
    if any(x in OMIT_NAMES or x.startswith(".env") and x != ".env.example" for x in p.parts):
        return False
    return p.suffix.lower() not in OMIT_EXT

def validate_source(item: Item) -> None:
    if not source_allowed(item.path):
        raise ValueError("Disallowed source path: " + item.path)
    if len(item.data) > MAX_SIZE:
        raise ValueError("File exceeds dry-run size limit")
    if any(rx.search(item.data) for rx in TOKEN):
        raise ValueError("Private credential signature in " + item.path)
    if item.path.endswith(".env.example"):
        for line in item.data.splitlines():
            line = line.strip().lstrip(b"# ").strip()
            for prefix in (b"APP_KEY=", b"DB_PASSWORD=", b"MAIL_PASSWORD="):
                if line.startswith(prefix) and line[len(prefix):] not in (b"", b"null", b"placeholder"):
                    raise ValueError("Credential in example env")

def load_git(root: Path) -> tuple[str, list[Item]]:
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    tree = subprocess.check_output(["git", "ls-tree", "-r", "-z", commit], cwd=root)
    files = []
    for record in tree.split(b"\0"):
        if not record:
            continue
        info, path = record.split(b"\t", 1)
        mode, kind, oid = info.split()
        name = path.decode()
        if not source_allowed(name):
            continue
        if mode == b"120000" or kind != b"blob":
            raise ValueError("Symlink or unsupported Git object: " + name)
        blob = subprocess.check_output(["git", "cat-file", "blob", oid.decode()], cwd=root)
        item = Item(name, blob)
        validate_source(item)
        files.append(item)
    if not files:
        raise ValueError("No approved committed sources")
    return commit, files

def role(name: str) -> str:
    if name.startswith("apps/"): return "application source / project configuration"
    if name.startswith("docs/"): return "document or demonstration template"
    if name.startswith("fixtures/"): return "synthetic demonstration data"
    if name.startswith("infra/"): return "deployment configuration example"
    if name.startswith("scripts/"): return "development tool"
    if name.startswith("tests/"): return "test source"
    if name.startswith(".github/"): return "CI configuration"
    return "root documentation/configuration"

def payload(commit: str, items: list[Item]) -> dict[str, bytes]:
    files = {}
    for item in items:
        validate_source(item)
        name = "source/" + item.path
        if name in files: raise ValueError("Duplicate path")
        files[name] = item.data
    if sum(len(data) for data in files.values()) > MAX_TOTAL: raise ValueError("Bundle too large")
    listing = [
        {"path": name, "bytes": len(data), "sha256": checksum(data), "role": role(name[7:])}
        for name, data in sorted(files.items())
    ]
    mem = io.StringIO(newline="")
    writer = csv.writer(mem, lineterminator="\n")
    writer.writerow(("path", "bytes", "sha256", "role", "rights_status"))
    for item in listing:
        writer.writerow((item["path"], item["bytes"], item["sha256"], item["role"], "not_verified"))
    files["INVENTORY.csv"] = mem.getvalue().encode()
    files["MANIFEST.json"] = jsonbytes({
        "git_commit": commit, "files": listing,
        "purpose": "PREAWARD_DEMONSTRATION_ONLY",
        "exclusive_rights_transferred": False, "customer_acceptance": False,
    })
    available = {PurePosixPath(item.path).suffix.lower() for item in items}
    files["STATUS.json"] = jsonbytes({
        "required_design_formats": {ext: "PRESENT_NOT_VERIFIED" if ext in available else "NOT_CREATED"
                                    for ext in REQUIRED},
        "museum_ticket_api": "NOT_CONNECTED",
        "museum_infrastructure": "NOT_DEPLOYED",
        "license_audit": "PENDING",
    })
    files["README_FIRST.md"] = (
        "# MusBread — ДЕМОНСТРАЦИЯ КОМПЛЕКТА, НЕ ПРИЁМКА\n\n"
        "Передача исключительных прав НЕ осуществлена. Исходники сторонних библиотек "
        "не являются собственными результатами разработчика. См. "
        "source/docs/handoff/RIGHTS_MATRIX.md и source/docs/THIRD_PARTY.md.\n\n"
        "В пакете нет реальных API-ключей, ПДн, рабочей базы музея и не созданных форматов.\n"
        "STATUS.json показывает отсутствующие результаты, а MANIFEST.json — хеши.\n"
        "Проверка: python3 source/scripts/handoff_bundle.py verify имя.zip\n"
        "Для фактической передачи нужен новый утверждённый релиз, проверка прав и "
        "отдельные носители/акты по договору.\n"
    ).encode()
    files["SHA256SUMS"] = "".join(
        checksum(files[name]) + "  " + name + "\n"
        for name in sorted(files)
    ).encode()
    return files

def create(path: Path, files: dict[str, bytes]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for name in sorted(files):
            info = zipfile.ZipInfo(name, ZIP_TIME)
            info.external_attr = 0o100644 << 16
            info.create_system = 3
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, files[name], compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)

def verify(path: Path) -> dict:
    with zipfile.ZipFile(path) as z:
        meta = z.infolist()
        names = [item.filename for item in meta]
        if len(set(names)) != len(names):
            raise ValueError("Duplicate ZIP paths")
        if any(n.startswith("/") or ".." in PurePosixPath(n).parts or "\\" in n or n.endswith("/") for n in names):
            raise ValueError("Unsafe ZIP path")
        if any(((item.external_attr >> 16) & 0o170000) == 0o120000 for item in meta):
            raise ValueError("Symlink in ZIP")
        if any(item.file_size > MAX_SIZE for item in meta) or sum(x.file_size for x in meta) > MAX_TOTAL:
            raise ValueError("ZIP size limit exceeded")
        if not EXTRA.issubset(names):
            raise ValueError("Missing manifest files")
        files = {name: z.read(name) for name in names}
    source_names = {n for n in names if n.startswith("source/")}
    if not source_names or set(names) != source_names | EXTRA:
        raise ValueError("Undeclared files in ZIP")
    for name in source_names:
        validate_source(Item(name[7:], files[name]))
    sums = [checksum(files[name]) + "  " + name for name in sorted(files) if name != "SHA256SUMS"]
    if files["SHA256SUMS"].decode().splitlines() != sums:
        raise ValueError("SHA256SUMS mismatch")
    manifest = json.loads(files["MANIFEST.json"])
    if manifest["purpose"] != "PREAWARD_DEMONSTRATION_ONLY" or manifest["exclusive_rights_transferred"] is not False:
        raise ValueError("Unjustified transfer claim")
    entries = manifest["files"]
    if {row["path"] for row in entries} != source_names or len(entries) != len(source_names):
        raise ValueError("Missing/duplicate manifest entries")
    for row in entries:
        data = files[row["path"]]
        if checksum(data) != row["sha256"] or len(data) != row["bytes"]:
            raise ValueError("Source checksum mismatch")
    records = list(csv.DictReader(io.StringIO(files["INVENTORY.csv"].decode())))
    if {row["path"] for row in records} != source_names or len(records) != len(source_names):
        raise ValueError("Inventory mismatch")
    status = json.loads(files["STATUS.json"])
    if status.get("license_audit") != "PENDING" or not status.get("required_design_formats"):
        raise ValueError("Missing status warnings")
    return {"source_files": len(source_names), "package_files": len(files)}

def main():
    parser = argparse.ArgumentParser()
    subs = parser.add_subparsers(dest="command", required=True)
    b = subs.add_parser("build")
    b.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    b.add_argument("--output", required=True, type=Path)
    v = subs.add_parser("verify")
    v.add_argument("archive", type=Path)
    args = parser.parse_args()
    if args.command == "verify":
        print("VERIFIED", verify(args.archive))
    else:
        commit, items = load_git(args.root)
        create(args.output, payload(commit, items))
        print("PACKAGED", verify(args.output), "git=", commit[:10], "SHA256=", checksum(args.output.read_bytes()))
        print("PRE-AWARD ONLY; NOT A LEGAL HANDOVER")

if __name__ == "__main__":
    main()
