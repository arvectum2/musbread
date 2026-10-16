#!/usr/bin/env python3
"""CP-33D: evidence-based pre-award license inventory of direct locked deps.

Provenance: composer.lock and package-lock.json; plus explicitly labelled
manually observed embedded TinyMCE assets and locally installed design tools.
The tool never certifies relicensing, commercial use, or IP transfer.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LICENSE_RISKS = ("GPL-", "LGPL-", "AGPL-", "MPL-")
PROD_PHP = (
    "ezyang/htmlpurifier","laravel/framework","moonshine/moonshine","moonshine/tinymce",
)
PROD_WEB = ("next","react","react-dom","sanitize-html")
DESIGN_PYTHON = (
    ("python-pptx","1.0.2","MIT","Installed python-pptx dist metadata on Mac mini; version pinned in requirements"),
    ("pypdf","5.6.1","BSD family (classifier, exact version needs manual legal confirmation)",
     "Installed pypdf dist metadata on Mac mini; version pinned in requirements"),
)


def audit(root:Path=ROOT, check_vendor:bool=False)->dict:
    composer=json.loads((root/"apps/cms/composer.lock").read_text(encoding="utf-8"))
    nlock=json.loads((root/"apps/web/package-lock.json").read_text(encoding="utf-8"))
    declared=json.loads((root/"apps/cms/composer.json").read_text(encoding="utf-8"))
    webdecl=json.loads((root/"apps/web/package.json").read_text(encoding="utf-8"))
    py_requirements=(root/"scripts/requirements-design-tools.txt").read_text(encoding="utf-8").splitlines()
    php={x["name"]:x for x in composer["packages"]}
    node=nlock["packages"]
    entries=[]
    for name in PROD_PHP:
        if name not in declared["require"] or name not in php:
            raise ValueError("Missing required direct PHP dependency: "+name)
        item=php[name]
        license_ids=item.get("license") or []
        if not license_ids:
            raise ValueError("Composer lock missing license: "+name)
        entries.append({
            "name":name,"ecosystem":"composer","version":item["version"],"declared_licenses":license_ids,
            "evidence":"apps/cms/composer.lock", "direct_runtime":True,
            "redistributed_upstream_code_owned_by_arvectum":False,
            "license_review":"REQUIRED" if any(tag in value for value in license_ids for tag in LICENSE_RISKS) else "NOTICE_AND_COMPLIANCE_REQUIRED",
        })
    for name in PROD_WEB:
        if name not in webdecl["dependencies"]:
            raise ValueError("Missing direct web runtime dependency "+name)
        item=node.get("node_modules/"+name)
        if not item or not item.get("license") or not item.get("version"):
            raise ValueError("Npm lock missing license or version: "+name)
        entries.append({
            "name":name,"ecosystem":"npm","version":item["version"],"declared_licenses":[item["license"]],
            "evidence":"apps/web/package-lock.json","direct_runtime":True,
            "redistributed_upstream_code_owned_by_arvectum":False,
            "license_review":"REQUIRED" if any(tag in item["license"] for tag in LICENSE_RISKS) else "NOTICE_AND_COMPLIANCE_REQUIRED",
        })
    for name,version,license_info,evidence in DESIGN_PYTHON:
        if f"{name}=={version}" not in py_requirements:
            raise ValueError("Design tool pin changed; manual license evidence must be refreshed: "+name)
        entries.append({
            "name":name,"ecosystem":"python-design-only","version":version,
            "declared_licenses":[license_info],"evidence":evidence,"direct_runtime":False,
            "redistributed_upstream_code_owned_by_arvectum":False,
            "license_review":"VERIFY_EXACT_LICENSE_AND_NOTICES",
        })
    # Distinguish MIT MoonShine TinyMCE integration from the EMBEDDED editor.
    wrapper=next(x for x in entries if x["name"]=="moonshine/tinymce")
    if wrapper["declared_licenses"]!=["MIT"]:
        raise ValueError("MoonShine TinyMCE wrapper license changed; stop and review")
    bundled_license=root/"apps/cms/vendor/moonshine/tinymce/public/license.md"
    if bundled_license.is_file():
        actual=bundled_license.read_text(encoding="utf-8")
        if not re.search("General Public License Version 2 or later",actual,re.I):
            raise ValueError("Embedded TinyMCE license has changed, must manually review")
    elif check_vendor:
        raise ValueError("Missing installed embedded TinyMCE license, cannot verify vendored CMS")
    entries.append({
        "name":"tinymce/embedded-runtime", "ecosystem":"bundled-javascript", "version":"UNVERIFIED_ASSET_VERSION",
        "declared_licenses":["GPL-2.0-or-later"],
        "evidence":"apps/cms/vendor/moonshine/tinymce/public/license.md (vendored, not tracked), independently listed in docs/THIRD_PARTY.md",
        "direct_runtime":True,"redistributed_upstream_code_owned_by_arvectum":False,
        "license_review":"BLOCKS_EXCLUSIVE_IP_CLAIM_UNTIL_LEGAL_REVIEW_OR_REPLACEMENT",
    })
    entries.append({
        "name":"librsvg/native-rsvg-convert","ecosystem":"native-build-tool","version":"SYSTEM_VERSION_NOT_PINNED",
        "declared_licenses":["REQUIRES_NATIVE_PACKAGE_LICENSE_INVENTORY"],
        "evidence":"Native Mac / Linux package outside locked application dependency tree",
        "direct_runtime":False,"redistributed_upstream_code_owned_by_arvectum":False,
        "license_review":"CONFIRM_NATIVE_TOOL_LICENSES_AND_DISTRIBUTION_BEFORE_DELIVERY",
    })
    mandatory_risk=[
        "TinyMCE runtime GPL-2.0-or-later vs MIT integration: must assess distribution and replacement/obligations",
        "HTMLPurifier LGPL-2.1-or-later: comply with notice, attribution and replacement rights",
        "Original source copyright ownership/contractor IP chain and third-party content is NOT audited",
        "Fonts and photos for customer-specific brand do not exist: actual licenses require documentation",
        "Native libre renderer build tools and transitive npm/composer dependencies need a full SBOM before delivery",
        "No library is transferred under exclusive Arvectum ownership; rights act must carve out all third party parts",
    ]
    return {
        "mode":"PREAWARD_LOCKFILE_EVIDENCE_NO_LEGAL_CONCLUSION",
        "contract_ready":False,"third_party_exclusive_rights_transfer":False,
        "all_licenses_legally_cleared":False,
        "inventory_scope":"SELECTED_DIRECT_RUNTIME_AND_DESIGN_DEPENDENCIES_ONLY_NOT_FULL_SBOM",
        "entries":entries,"mandatory_reviews":mandatory_risk,
        "summary":{"direct_php":len(PROD_PHP),"direct_web":len(PROD_WEB),
                   "design_python":len(DESIGN_PYTHON),"embedded_gpl_bundles":1,
                   "license_review_blockers":len(mandatory_risk)},
    }


def markdown(data:dict)->str:
    lines=[
        "# MusBread — CP-33D direct dependency and rights audit","",
        "**Not a full SBOM or legal approval.** Metadata in local lock files documents license declarations; it does not prove redistribution compliance or ownership.","",
        "| Component | Locked version | Declared license | Evidence | Delivery review |",
        "|---|---|---|---|---|",
    ]
    for x in data["entries"]:
        vals=(x["name"],x["version"],", ".join(x["declared_licenses"]),x["evidence"],x["license_review"])
        lines.append("| "+" | ".join(v.replace("|","/").replace("\n"," ") for v in vals)+" |")
    lines+=["","## Mandatory legal and customer gates",""]
    lines+=["- "+x for x in data["mandatory_reviews"]]
    lines+=["","## Interpretation","",
        "- moonshine/tinymce is an MIT-licensed integration layer per composer.lock and vendored LICENSE.md.",
        "- Its public editor runtime has a SEPARATE GPL-2.0-or-later notice in the locally installed public/license.md. Never infer editor license from the wrapper.",
        "- pypdf's observed packaging classifier indicates BSD family; this report does not assert exact legally binding text. Verify installed LICENSE text.",
        "- Fonts, logos, text, customer media and third-party services are not cleared by dependency locks.",
        "- Avoid distributing vendor/node_modules in the public pre-award handoff. Official delivery must address whether/how such code is transferred.",
        "- Reviewed direct dependencies only; transitive, browser bundled chunks and native binary provenance need a full SBOM.",
        ""]
    return "\n".join(lines)


def main()->int:
    p=argparse.ArgumentParser()
    p.add_argument("--root",type=Path,default=ROOT)
    p.add_argument("--json",type=Path)
    p.add_argument("--markdown",type=Path)
    p.add_argument("--check-vendor",action="store_true")
    p.add_argument("--verify-generated",action="store_true")
    args=p.parse_args()
    result=audit(args.root,args.check_vendor)
    for path,value in ((args.json,json.dumps(result,ensure_ascii=False,indent=2)+"\n"),
                       (args.markdown,markdown(result))):
        if path:
            if args.verify_generated:
                if not path.is_file() or path.read_text(encoding="utf-8")!=value:
                    raise ValueError("Stale rights report "+str(path))
            else:
                path.parent.mkdir(parents=True,exist_ok=True)
                path.write_text(value,encoding="utf-8")
    print("RIGHTS/LCKFILE QA:",result["summary"],
          "LEGAL_APPROVAL",result["all_licenses_legally_cleared"])
    return 0


if __name__=="__main__":
    raise SystemExit(main())
