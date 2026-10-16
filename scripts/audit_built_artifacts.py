#!/usr/bin/env python3
"""CP-35D. Read-only inventory of ACTUAL build files and installed Composer tree.

The audit differentiates three fundamentally different artifacts:
- public Next.js static export (compiled JS provenance cannot be assumed from lock);
- private CMS public vendor assets and installed Composer package code;
- committed source-only pre-award ZIP (explicitly excludes installed vendor).
No original vendor code or client data is copied into evidence.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import re
import zipfile
from collections import Counter
from pathlib import Path
from typing import Any

import sys
if str(Path(__file__).resolve().parents[1]) not in sys.path:
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

from scripts.audit_public_artifacts import audit as check_public
from scripts.handoff_bundle import verify as verify_bundle

ROOT=Path(__file__).resolve().parents[1]
STATIC_TYPES={".js",".css",".svg",".png",".jpg",".jpeg",".woff",".woff2",
              ".ico",".json",".txt",".md",".ts",".gif",".map"}
WEB_TYPES={".js",".css",".woff",".woff2",".html",".png",".jpg",".jpeg",".webp",
           ".svg",".ico",".json",".txt",".xml",".pdf",".docx",".xlsx"}
BAD_PATHS=("..",)
TINY_LICENSE="GNU General Public License Version 2 or later"

def sha_file(path: Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda:stream.read(256*1024),b""):h.update(block)
    return h.hexdigest()


def collect(root:Path, allowed:set[str], *, source:str)->tuple[list[dict[str,Any]],dict[str,int]]:
    if not root.is_dir() or root.is_symlink():
        raise ValueError("Missing/unsafe "+source+" root directory")
    rows=[]
    sizes=Counter()
    for path in sorted(root.rglob("*")):
        if path.is_symlink():raise ValueError("Symlink in "+source+": "+str(path))
        if not path.is_file():continue
        relative=path.relative_to(root).as_posix()
        ext=path.suffix.lower()
        if ext not in allowed:
            raise ValueError("Unexpected "+source+" asset extension: "+relative)
        if any(x in BAD_PATHS for x in path.relative_to(root).parts) or relative.startswith("."):
            raise ValueError("Unsafe artifact path")
        size=path.stat().st_size
        rows.append({"path":relative,"bytes":size,"sha256":sha_file(path),
                     "suffix":ext})
        sizes[ext]+=1
    return rows,dict(sorted(sizes.items()))


def web_report(root:Path)->dict:
    # Security checks from previous audits must remain in this gate.
    check_public(root)
    rows,types=collect(root,WEB_TYPES,source="Next public export")
    compiled=[row for row in rows if row["path"].startswith("_next/static/")
              and row["suffix"] in (".js",".css")]
    if not compiled or not any(x["path"]=="index.html" for x in rows):
        raise ValueError("Next compiled assets or index.html missing")
    if any(x["path"].endswith(".map") for x in rows):
        raise ValueError("Unexpected publicly accessible sourcemap")
    return {
        "kind":"ACTUAL_PREAWARD_STATIC_NEXT_EXPORT",
        "root_visibility":"PUBLIC_ONLY_NOT_CMS",
        "files":rows,"files_total":len(rows),"bytes_total":sum(x["bytes"] for x in rows),
        "types":types,"compiled_js_css_count":len(compiled),
        "bundled_third_party_component_map":"NOT_ESTABLISHED_FROM_MINIFIED_JS",
        "source_lockfile_provenance":"CANDIDATE_ONLY_NEEDS_REAL_BUNDLE_ANALYSIS",
        "external_binary_license_approved":False,
        "security_rule_check":"PASSED_PROTOTYPE_RULES_NOT_PENTEST",
        "museum_production_delivery":False,
    }


def cms_report(public:Path,vendor:Path,composer_lock:Path,*,install_profile:str="all")->dict:
    if install_profile not in ("all","production"):
        raise ValueError("Unsupported Composer install profile")
    root=public/"vendor"
    rows,types=collect(root,STATIC_TYPES,source="private CMS public vendor")
    if not rows:raise ValueError("CMS installed public assets missing")
    required={"moonshine/assets/app.js","moonshine/assets/main.css",
              "moonshine-tinymce/tinymce.min.js",
              "moonshine-tinymce/license.md"}
    found={row["path"] for row in rows}
    if not required.issubset(found):
        raise ValueError("Installed CMS asset expected but missing: "+str(sorted(required-found)))
    # Scope the Nginx allowlist to verified static vendor files only.
    if any(not x["path"].startswith(("moonshine/","moonshine-tinymce/")) for x in rows):
        raise ValueError("Unexpected private CMS vendor namespace")
    license_path=root/"moonshine-tinymce/license.md"
    actual=license_path.read_text(encoding="utf-8")
    if TINY_LICENSE not in actual:
        raise ValueError("Installed TinyMCE GPL notice missing/changed")
    tiny_path=root/"moonshine-tinymce/tinymce.min.js"
    with tiny_path.open("rb") as tiny_stream:
        version=re.search(rb"TinyMCE version\s+([0-9.]+)",tiny_stream.read(350),re.I)
    if not version:raise ValueError("Bundled TinyMCE JS version cannot be identified")
    fonts=[{"path":x["path"],"sha256":x["sha256"],"bytes":x["bytes"],
            "license":"UNVERIFIED_LICENSE_FOR_MUSEUM_REDISTRIBUTION"}
           for x in rows if x["path"].lower().endswith((".woff",".woff2",".ttf",".otf"))]
    installed=vendor/"composer/installed.json"
    if not installed.is_file():raise ValueError("Composer installed.json missing")
    info=json.loads(installed.read_text(encoding="utf-8"))
    pkgs=info["packages"] if isinstance(info,dict) else info
    locked=json.loads(composer_lock.read_text(encoding="utf-8"))
    prod=locked["packages"]
    dev=locked["packages-dev"]
    all_names=[p["name"] for p in prod+dev]
    if len(all_names)!=len(set(all_names)):
        raise ValueError("Duplicate Composer locked name")
    chosen=prod if install_profile=="production" else prod+dev
    wanted={p["name"]:p for p in chosen}
    dev_names={p["name"] for p in dev}
    if install_profile=="production" and isinstance(info,dict):
        if info.get("dev") is True or info.get("dev-package-names"):
            raise ValueError("Composer production install includes dev metadata")
    packages=[]
    installed_names=set()
    for pkg in sorted(pkgs,key=lambda x:x["name"]):
        name=pkg["name"]
        if name in installed_names:
            raise ValueError("Duplicate installed Composer name: "+name)
        installed_names.add(name)
        if name not in wanted or pkg["version"]!=wanted[name]["version"]:
            raise ValueError("Installed Composer dependency differs from lockfile: "+name)
        ref=wanted[name]
        parts=name.split("/")
        on_disk=vendor/parts[0]/parts[1]
        if not on_disk.is_dir() or on_disk.is_symlink():
            raise ValueError("Composer installed tree missing/unsafe: "+name)
        files=0;bytes_total=0
        h=hashlib.sha256()
        for f in sorted(on_disk.rglob("*")):
            if f.is_symlink():raise ValueError("Composer vendor symlink: "+str(f))
            if not f.is_file():continue
            rel=f.relative_to(on_disk).as_posix()
            digest=sha_file(f)
            size=f.stat().st_size
            h.update((rel+"\0"+str(size)+"\0"+digest+"\n").encode())
            files+=1;bytes_total+=size
        packages.append({
            "name":name,"version":pkg["version"],
            "scope":"development_installed" if name in dev_names else "production_installed",
            "licenses_declared_by_lock":ref.get("license",[]),
            "files":files,"bytes":bytes_total,"tree_sha256":h.hexdigest(),
        })
    if installed_names!=set(wanted):
        missing=sorted(set(wanted)-installed_names)
        extra=sorted(installed_names-set(wanted))
        raise ValueError(f"Installed Composer names do not match {install_profile} lockfile profile: missing={missing}, extra={extra}")
    return {
        "kind":"ACTUAL_LOCAL_CMS_VENDOR_INSTALL_NOT_CUSTOMER_DEPLOYMENT",
        "visibility":"PRIVATE_CMS_LISTENER_ONLY",
        "public_vendor_assets":rows,"public_vendor_asset_types":types,
        "public_vendor_count":len(rows),"public_vendor_bytes":sum(x["bytes"] for x in rows),
        "installed_composer_packages":packages,
        "installed_package_count":len(packages),
        "composer_install_profile":install_profile,
        "production_locked_package_count":len(prod),
        "development_locked_package_count":len(dev),
        "development_packages_installed":len(installed_names&dev_names),
        "production_profile_verified":install_profile=="production" and not (installed_names&dev_names),
        "installed_vendor_files":sum(x["files"] for x in packages),
        "embedded_tinymce_version":version.group(1).decode(),
        "embedded_tinymce_license":"GPL-2.0-or-later_NOTICE_OBSERVED",
        "tiny_mce_removal_status":"STILL_INSTALLED",
        "bundled_script_and_font_rights":"NOT_LEGALLY_CLEARED",
        "font_license_blockers":fonts,
        "binary_assets_mapped_exactly_to_lock":"NOT_PROVED_FOR_COMPILED_MOONSHINE",
        "museum_production_delivery":False,
    }


def zip_report(bundle:Path)->dict:
    result=verify_bundle(bundle)
    with zipfile.ZipFile(bundle) as z:
        names=z.namelist()
        if any(x.startswith(("source/apps/web/out/","source/apps/cms/vendor/",
                              "source/apps/cms/public/vendor/","source/apps/web/node_modules/")) for x in names):
            raise ValueError("Pre-award source ZIP accidentally contains installed binaries/vendor")
        status=json.loads(z.read("STATUS.json"))
        if status.get("license_audit")!="PENDING" or status.get("exclusive_rights_transferred") is True:
            raise ValueError("Source demo ZIP misrepresents license/rights status")
        if "source/docs/handoff/SBOM_CYCLONEDX.json" not in names:
            raise ValueError("Demonstration ZIP SBOM missing")
    return {"kind":"PREAWARD_GIT_COMMITTED_SOURCE_BUNDLE",
            "zip_sha256":sha_file(bundle),"zip_bytes":bundle.stat().st_size,
            "source_files":result["source_files"],
            "vendor_or_build_assets_included":False,
            "legal_rights":"PENDING_NO_OWNERSHIP_TRANSFER",
            "museum_production_delivery":False}


def run(args:argparse.Namespace)->dict:
    if args.mode=="web":
        data=web_report(args.web)
    elif args.mode=="cms":
        data=cms_report(args.cms_public,args.cms_vendor,args.composer_lock,install_profile=args.composer_profile)
    elif args.mode=="source-zip":
        data=zip_report(args.zip)
    else:raise ValueError("Unsupported artifact mode")
    return {"audit":"CP35_REAL_FILES_SNAPSHOT_NOT_CUSTOMER_PRODUCTION",
            "mode":args.mode,"result":data,"legal_clearance":False,
            "physical_museum_acceptance":False}


def main()->None:
    p=argparse.ArgumentParser()
    p.add_argument("--mode",required=True,choices=["web","cms","source-zip"])
    p.add_argument("--web",type=Path,default=ROOT/"apps/web/out")
    p.add_argument("--composer-profile",choices=["all","production"],default="all",
                   help="Expected installed Composer package profile; production rejects all dev packages")
    p.add_argument("--cms-public",type=Path,default=ROOT/"apps/cms/public")
    p.add_argument("--cms-vendor",type=Path,default=ROOT/"apps/cms/vendor")
    p.add_argument("--composer-lock",type=Path,default=ROOT/"apps/cms/composer.lock")
    p.add_argument("--zip",type=Path)
    p.add_argument("--out",type=Path)
    opts=p.parse_args()
    if opts.mode=="source-zip" and opts.zip is None:
        raise ValueError("--zip must be supplied with source-zip mode")
    data=run(opts)
    if opts.out:
        opts.out.parent.mkdir(parents=True,exist_ok=True)
        opts.out.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n")
    obj=data["result"]
    print("CP35",opts.mode,"actual_files",obj.get("files_total",obj.get("public_vendor_count",obj.get("source_files"))),
          "legal_clearance",data["legal_clearance"])


if __name__=="__main__":
    main()
