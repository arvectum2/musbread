#!/usr/bin/env python3
"""CP-34D: deterministic CycloneDX 1.6 pre-award inventory from lockfiles.

Enumerates ALL locked Node and Composer records, dev and optional included.
Includes build tools and self-hosted MIT Jodit Community runtime.
Does not claim legal clearance, reproducible binary installation, or production
shipment of every platform-specific optional locked package.
"""
from __future__ import annotations
import argparse
import csv
import io
import json
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = {"apps/cms/composer.lock", "apps/cms/composer.json",
            "apps/web/package-lock.json", "apps/web/package.json",
            "scripts/requirements-design-tools.txt"}


def license_risk(value: str) -> str:
    v = value.upper()
    if not value.strip() or any(x in v for x in ("UNKNOWN","NOASSERTION","UNVERIFIED","UNSPECIFIED")):
        return "UNKNOWN_REQUIRES_VERIFICATION"
    if "AGPL" in v or "GPL-2.0" in v or "GPL-3.0" in v or v.startswith("GPL"):
        if "LGPL" in v and "GPL" not in v.replace("LGPL", ""):
            return "WEAK_COPYLEFT_LGPL"
        return "STRONG_COPYLEFT_OR_DUAL_REVIEW"
    if "LGPL" in v:
        return "WEAK_COPYLEFT_LGPL"
    if "MPL-" in v or "EPL-" in v or "CDDL" in v:
        return "FILE_LEVEL_COPYLEFT_REVIEW"
    if " AND " in v or " OR " in v or "," in v:
        return "COMPOUND_LICENSE_REVIEW"
    if v.startswith(("MIT", "APACHE-", "BSD-", "ISC", "0BSD", "CC0-", "PYTHON-2")):
        return "PERMISSIVE_NOTICE_CHECK"
    return "NON_STANDARD_OR_MANUAL_REVIEW"


def npm_resolve(path: str, dep: str, paths: set[str]) -> str | None:
    """Node's nearest node_modules search; handle nested/scoped modules."""
    if not dep or dep.startswith(".") or "\\" in dep or dep.startswith("/"):
        raise ValueError("Unsafe npm dependency name: "+dep)
    prefix = path
    while True:
        candidate = f"{prefix}/node_modules/{dep}" if prefix else f"node_modules/{dep}"
        if candidate in paths:
            return candidate
        if not prefix:
            return None
        if "/node_modules/" in prefix:
            prefix = prefix.rsplit("/node_modules/", 1)[0]
        elif prefix.startswith("node_modules/"):
            prefix = ""
        else:
            prefix = ""


def npm_package_name(path: str) -> str:
    if not path.startswith("node_modules/") and "/node_modules/" not in path:
        raise ValueError("Unsupported npm package key " + path)
    return path.rsplit("node_modules/", 1)[1]


def bom(root: Path = ROOT) -> dict:
    if not all((root / f).is_file() for f in REQUIRED):
        raise ValueError("Missing lockfile/requirements needed for complete SBOM")
    c = json.loads((root/"apps/cms/composer.lock").read_text())
    cdecl=json.loads((root/"apps/cms/composer.json").read_text())
    n=json.loads((root/"apps/web/package-lock.json").read_text())
    ndecl=json.loads((root/"apps/web/package.json").read_text())
    pin_lines=(root/"scripts/requirements-design-tools.txt").read_text().splitlines()
    if n.get("lockfileVersion") != 3 or not isinstance(n.get("packages"),dict):
        raise ValueError("Unrecognized npm lockfile format")
    if n["packages"].get("",{}).get("name") not in (ndecl.get("name"), None):
        raise ValueError("npm root package mismatch")
    if not isinstance(c.get("packages"),list) or not isinstance(c.get("packages-dev"),list):
        raise ValueError("Composer production and development lock records required")
    components=[]
    graph=defaultdict(set)
    details={}
    refmap={}
    provided_by={}
    unresolved=[]
    summary=Counter()

    def add(ref: str, name: str, version: str|None, kind: str, source: str,
            license_list: list[str], scope: str, direct: bool, optional: bool=False,
            platform: dict|None=None, extra: dict|None=None, purl: str|None=None)->None:
        if ref in details:
            raise ValueError("Duplicate SBOM reference "+ref)
        if not license_list: license_list=["UNSPECIFIED"]
        licenses=[str(x).strip() for x in license_list]
        maxrisk=sorted({license_risk(v) for v in licenses})
        props=[
            {"name":"musbread:source-lockfile","value":source},
            {"name":"musbread:dependency-scope","value":scope},
            {"name":"musbread:direct-dependency","value":str(direct).lower()},
            {"name":"musbread:optional-or-platform-specific","value":str(optional).lower()},
            {"name":"musbread:manual-license-risk","value":",".join(maxrisk)},
        ]
        for k,v in sorted((platform or {}).items()):
            if isinstance(v,list): v=",".join(v)
            props.append({"name":"musbread:platform-"+k,"value":str(v)})
        for k,v in sorted((extra or {}).items()):
            props.append({"name":"musbread:"+k,"value":str(v)})
        comp={"type":"library" if kind!="native-build" else "application",
              "bom-ref":ref,"name":name,"licenses":[{"license":{"name":z}} for z in licenses],
              "properties":props}
        if version:comp["version"]=version
        if purl:comp["purl"]=purl
        components.append(comp)
        details[ref]=dict(ref=ref,name=name,version=version or "",
                          ecosystem=kind,license=" OR ".join(licenses),
                          risk=";".join(maxrisk),scope=scope,direct=direct,
                          optional=optional,source=source)
        summary[kind]+=1
        # A component with BOTH GPL and BSD must appear in ONE high-risk
        # category, never inflate the number of components by double-counting.
        priority=("STRONG_COPYLEFT_OR_DUAL_REVIEW","WEAK_COPYLEFT_LGPL",
                  "FILE_LEVEL_COPYLEFT_REVIEW","COMPOUND_LICENSE_REVIEW",
                  "UNKNOWN_REQUIRES_VERIFICATION","NON_STANDARD_OR_MANUAL_REVIEW",
                  "PERMISSIVE_NOTICE_CHECK")
        chosen=next(label for label in priority if label in maxrisk)
        summary["risk:"+chosen]+=1

    for kind,items in (("composer",c["packages"]),("composer-dev",c["packages-dev"])):
        dev=kind=="composer-dev"
        for item in items:
            name=item["name"];ver=item["version"];ref=f"composer:{name}@{ver}"
            if name in refmap:raise ValueError("Duplicate composer package "+name)
            refmap[name]=ref
            # Composer packages may replace/provide virtual subpackages.
            # Laravel/framework replaces illuminate/*; these are not missing
            # locked packages and must not appear as unresolved dependencies.
            for alias in sorted(set(item.get("replace",{})) | set(item.get("provide",{}))):
                provided_by.setdefault(alias,ref)
            direct=name in cdecl.get("require-dev" if dev else "require",{})
            add(ref,name,ver,kind,"apps/cms/composer.lock",item.get("license",[]),
                "development" if dev else "production",direct,
                purl="pkg:composer/"+quote(name,safe="/")+"@"+quote(ver,safe=""))
    # Include every locked npm installed package record, even OS-incompatible
    # optional binaries and dev tooling. Root npm project itself is not a package.
    paths=set(n["packages"])-{""}
    for path in sorted(paths):
        item=n["packages"][path]
        name=npm_package_name(path)
        ref="npm:"+path
        scope="development" if item.get("dev") or item.get("devOptional") else "production_or_optional"
        direct=name in ndecl.get("devDependencies" if scope=="development" else "dependencies",{})
        # A direct package may also occur transitively: only root node_modules
        # matches the direct installation location.
        direct=direct and path=="node_modules/"+name
        optional=bool(item.get("optional") or item.get("devOptional"))
        add(ref,name,item.get("version"),"npm","apps/web/package-lock.json",
            [item.get("license") or "UNSPECIFIED"],scope,direct,optional,
            {k:item[k] for k in ("os","cpu","libc") if k in item},
            {"lockfile-path":path},
            "pkg:npm/"+quote(name,safe="/")+"@"+quote(item.get("version",""),safe=""))
    # Composer graph: real production/dev dependencies resolved from lock.
    for kind,items in (("composer",c["packages"]),("composer-dev",c["packages-dev"])):
        for item in items:
            ref=refmap[item["name"]]
            for dep in sorted(item.get("require",{})):
                if dep in refmap:
                    graph[ref].add(refmap[dep])
                elif dep in provided_by:
                    graph[ref].add(provided_by[dep])
                elif not dep.startswith(("php","ext-","lib-","composer-")):
                    unresolved.append({"from":ref,"target":dep,"kind":"composer","class":"external_or_virtual"})
    # Node graph. dev/optional/peer flags remain visible in individual records.
    for path in sorted(paths):
        item=n["packages"][path]
        ref="npm:"+path
        for typ in ("dependencies","optionalDependencies","peerDependencies"):
            for target in sorted(item.get(typ,{})):
                dest=npm_resolve(path,target,paths)
                if dest:
                    graph[ref].add("npm:"+dest)
                else:
                    unresolved.append({"from":ref,"target":target,"kind":typ,
                                       "class":"optional_or_peer" if typ!="dependencies" else "unresolved_runtime_dependency"})
    # Direct root references.
    rootref="musbread:source-project"
    for name in sorted(cdecl.get("require",{})):
        if name in refmap:graph[rootref].add(refmap[name])
    for name in sorted(cdecl.get("require-dev",{})):
        if name in refmap:graph[rootref].add(refmap[name])
    for section in ("dependencies","devDependencies"):
        for name in sorted(ndecl.get(section,{})):
            target="node_modules/"+name
            if target not in paths:
                raise ValueError("Missing npm root direct dependency "+name)
            graph[rootref].add("npm:"+target)
    python_entries=(("python-pptx","1.0.2","MIT"),
                    ("pypdf","5.6.1","BSD-family-classifier-exact-notice-verify"),
                    ("lxml","6.1.3","BSD-3-Clause;native-libxml2-libxslt-notices-review"))
    for name,ver,lic in python_entries:
        if f"{name}=={ver}" not in pin_lines:
            raise ValueError("Design dependency pin changed "+name)
        ref="pypi:"+name+"@"+ver
        add(ref,name,ver,"python-design","scripts/requirements-design-tools.txt",
            [lic],"build_only",True,purl=f"pkg:pypi/{name}@{ver}")
        graph[rootref].add(ref)
    add("embedded:jodit-runtime","Jodit Community WYSIWYG runtime","4.18.4",
        "bundled-asset","apps/cms/public/vendor/museum-jodit/LICENSE.txt (MIT, pinned npm 4.18.4)",
        ["MIT"],"CMS_RUNTIME",True,False,
        extra={"version-status":"PINNED","source-code-ownership":"THIRD_PARTY",
               "network-backend":"NONE","premium-components":"NONE"},
        purl="pkg:npm/jodit@4.18.4")
    graph[rootref].add("embedded:jodit-runtime")
    add("native:librsvg","librsvg/rsvg-convert",None,"native-build",
        "Mac mini / Linux package manager, outside lockfiles",
        ["UNVERIFIED_NATIVE_PACKAGE_LICENSE"],"build_only",False,True,
        extra={"version-status":"NOT_PINNED","redistributed-in-handoff":"false"})
    graph[rootref].add("native:librsvg")
    # Full SBOM records do not imply platform-specific installed binaries or
    # copyright compliance. Embedded JS may contain other dependencies.
    comp=sorted(components,key=lambda x:x["bom-ref"])
    deps=[{"ref":x["bom-ref"],"dependsOn":sorted(graph[x["bom-ref"]])} for x in comp]
    deps.append({"ref":rootref,"dependsOn":sorted(graph[rootref])})
    allrefs={x["bom-ref"] for x in comp}|{rootref}
    for item in deps:
        for dest in item["dependsOn"]:
            if dest not in allrefs:raise ValueError("Dangling SBOM dependency reference")
    return {
        "bomFormat":"CycloneDX","specVersion":"1.6","version":1,
        "metadata":{"component":{"type":"application","bom-ref":rootref,
                                 "name":"musbread-preaward-source","version":"0.0.0-preaward"},
                    "properties":[
                        {"name":"musbread:legal-status","value":"NOT_A_LEGAL_CLEARANCE"},
                        {"name":"musbread:scope","value":"ALL_LOCKED_PRODUCTION_DEV_OPTIONAL_BUT_NOT_FULL_BINARY_SBOM"},
                        {"name":"musbread:source","value":"composer.lock + package-lock.json + design-pins + self-hosted Jodit MIT notice"},
                    ]},
        "components":comp,
        "dependencies":deps,
        "properties":[{"name":"musbread:unresolved_dependency_edges","value":str(len(unresolved))}],
    },details,unresolved,dict(sorted(summary.items()))


def report(root:Path=ROOT)->tuple[dict,str,str]:
    data,details,unresolved,counts=bom(root)
    # Pinned values come from the actual complete lockfile, never estimates.
    summary={
        "status":"LOCKFILE_SBOM_NOT_COMPLIANCE_APPROVAL",
        "total_components":len(data["components"]),
        "composer_production":counts["composer"],
        "composer_development":counts["composer-dev"],
        "npm_all_locked":counts["npm"],
        "python_design":counts["python-design"],
        "bundled_assets":counts["bundled-asset"],
        "native_build_tools":counts["native-build"],
        "risk_classification_counts":{k.removeprefix("risk:"):v for k,v in counts.items() if k.startswith("risk:")},
        "unresolved_lockfile_edges":len(unresolved),
        "unresolved_edge_examples":unresolved[:35],
        "embedded_editor":{"name":"Jodit Community 4.18.4","license_notice":"MIT",
                           "source":"locally vendored original npm tarball",
                           "requires_notice_preserved":True,
                           "open":{"license_text_verified":False,"all_distributed_components_reviewed":False}},
        "legal_clearance":False,
        "transferred_exclusive_third_party_rights":False,
        "limitations":[
            "Lockfile components are not necessarily installed or shipped on target OS",
            "Unknown licenses and mixed expressions require verification against original texts",
            "CycloneDX graph includes resolved peer and optional dependency relationships",
            "Source packages do not prove provenance of built/minified vendored bundles",
            "Jodit Community MIT license notice must accompany all distributed copies",
            "Native renderer version/license and some transitive binary assets outside locks are unknown",
            "No museum artwork, employee/contractor rights or customer approvals have been audited",
        ],
    }
    out=io.StringIO(newline="")
    writer=csv.writer(out,lineterminator="\n")
    writer.writerow(("bom_ref","name","version","ecosystem","scope","direct","optional","declared_license","license_risk","source"))
    for ref,row in sorted(details.items()):
        writer.writerow((row["ref"],row["name"],row["version"],row["ecosystem"],row["scope"],
                         int(row["direct"]),int(row["optional"]),row["license"],row["risk"],row["source"]))
    return data,json.dumps(summary,ensure_ascii=False,indent=2)+"\n",out.getvalue()


def summary_markdown(summary:dict)->str:
    risk=summary["risk_classification_counts"]
    lines=[
        "# MusBread CP-34D — SBOM for all locked source dependencies",
        "",
        "**Pre-award source dependency inventory, not a legal sign-off or installed-binary SBOM.**",
        "",
        "| Package source | Entries |",
        "|---|---:|",
        f"| Composer production | {summary['composer_production']} |",
        f"| Composer development | {summary['composer_development']} |",
        f"| npm all locked (including optional platform and dev) | {summary['npm_all_locked']} |",
        f"| Pinned design Python tools | {summary['python_design']} |",
        f"| Explicit embedded editor asset | {summary['bundled_assets']} |",
        f"| Native build tool | {summary['native_build_tools']} |",
        f"| **Total distinct component records** | **{summary['total_components']}** |",
        "",
        "## Declared license risk buckets (one highest-priority bucket per component)",
        "",
        "| Triage bucket | Count |",
        "|---|---:|",
    ]
    for name,count in sorted(risk.items()):
        lines.append(f"| {name} | {count} |")
    lines += [
        "",
        "Risk categories are triage signals, NOT legal conclusions. An SPDX OR alternative",
        "does not force use of GPL; inspect original license and document chosen conditions.",
        "Components may be optional on a target OS, build-only or dev-only.",
        "",
        "## High-priority review",
        "",
        "- Jodit Community is locally vendored under MIT; the copyright/license notice is mandatory.",
        "- Composer nette/schema and nette/utils declare BSD-3-Clause OR GPL choices;",
        "  review alternatives and notices, do not call them GPL-only.",
        "- HTMLPurifier LGPL-2.1-or-later and platform-optional sharp/libvips",
        "  declare LGPL-3.0-or-later and compound licenses in the Node lock.",
        "- MPL-2.0 is present in axe-core and @axe-core/playwright test dependencies.",
        "- BlueOak-1.0.0, CC-BY-4.0, native renderer and pypdf BSD notice require separate review.",
        "",
        f"Unresolved dependency graph references: **{summary['unresolved_lockfile_edges']}**;",
        "only optional peer targets remain, not missing locked mandatory runtime packages.",
        "",
        "## Complete sources",
        "",
        "- SBOM_CYCLONEDX.json: CycloneDX 1.6 all locked components and resolved graph.",
        "- SBOM_LICENSES.csv: per-component source, exact declared license and triage.",
        "- SBOM_SUMMARY.json: counted values, unmatched optional edges and limitations.",
        "",
        "## Legal and delivery boundaries",
        "",
        "- All locked Composer/npm production, dev and platform-optional records included.",
        "- Two pinned Python design tools, bundled Jodit CE MIT and one native renderer disclosed.",
        "- This does NOT establish an optional OS package is installed or distributed.",
        "- Built vendored bundles, original license notices and transitive binaries still need inspection.",
        "- Final deployment needs a new installed-binary artifact/SBOM comparison.",
        "- Third-party exclusive rights are not owned by Arvectum.",
        "- Museum-approved final design: 0/113.",
        "",
    ]
    return "\n".join(lines)


def write_or_check(root:Path,verify:bool)->dict:
    data,summary,csvtext=report(root)
    output={
        root/"docs/handoff/SBOM_CYCLONEDX.json":json.dumps(data,ensure_ascii=False,indent=2)+"\n",
        root/"docs/handoff/SBOM_SUMMARY.json":summary,
        root/"docs/handoff/SBOM_LICENSES.csv":csvtext,
        root/"docs/handoff/SBOM_SUMMARY.md":summary_markdown(json.loads(summary)),
    }
    for path,content in output.items():
        if verify:
            if not path.is_file() or path.read_text(encoding="utf-8")!=content:
                raise ValueError("Missing/stale lockfile SBOM artifact "+str(path))
        else:
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text(content,encoding="utf-8")
    return json.loads(summary)


def main()->None:
    p=argparse.ArgumentParser()
    p.add_argument("--root",type=Path,default=ROOT)
    p.add_argument("--verify-generated",action="store_true")
    args=p.parse_args()
    print("CP34 SBOM",write_or_check(args.root,args.verify_generated)["total_components"],"locked and disclosed components")


if __name__=="__main__":
    main()
