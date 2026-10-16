#!/usr/bin/env python3
"""CP-33D: validate native *technical drafts* and identify missing final formats.

Never equate the presence of a technical SVG/PPTX/PDF/PNG with a customer
approved final design, print-ready CMYK or legally transferable source.
"""
from __future__ import annotations

import argparse
import json
import math
from collections import Counter
from pathlib import Path

from scripts.audit_design_delivery import define
from scripts.generate_technical_carriers import OUTPUT as PRINT_ROOT, verify as verify_print
from scripts.generate_secondary_carriers import OUTPUT as SECOND_ROOT, verify as verify_secondary
from scripts.generate_digital_merch_carriers import OUTPUT as DIGITAL_ROOT, verify as verify_digital

ROOT = Path(__file__).resolve().parents[1]
FINAL = {
    ".ai": ("TZ-066,TZ-071", "Editable Adobe Illustrator native source", "Native open/edit/re-save in Illustrator and font/license check"),
    ".eps": ("TZ-066,TZ-071", "Editable EPS vector", "Open/edit/re-save, separated shapes, true vector scaling"),
    ".svg": ("TZ-066,TZ-071", "Editable SVG vector", "Original, approved logo/design, live text/path editing and safety"),
    ".psd": ("TZ-067", "Layered PSD master", "Photoshop native layer editing"),
    ".tiff": ("TZ-067,TZ-068", "Raster TIFF final", "True 300dpi at print size, color profile and visual content"),
    ".pdf": ("TZ-069", "Final viewing/print PDF", "Pages, fonts, embedded media and color/print profile by print shop"),
    ".jpg": ("TZ-069,TZ-071", "Final JPG", "Decode, output dimensions and licensed source"),
    ".png": ("TZ-069,TZ-071", "Final PNG", "Decode, output dimensions and content quality"),
    ".ppt": ("TZ-070", "Legacy editable PPT", "Open-edit-resave in native PowerPoint (OOXML PPTX does not cover .ppt)"),
    ".pptx": ("TZ-070", "OpenXML editable PPTX", "Open-edit-resave text & shapes in PowerPoint, approved fonts"),
}
# Digital PNG previews have pixels, but do NOT have any known physical
# target size or manufacturing printer specification.
SUPPLIED = {
    ".svg": "42 editable geometric drafts (not approved design)",
    ".pdf": "26 vector technical PDF previews (not print masters)",
    ".png": "16 technical previews (not print-resolution masters)",
    ".pptx": "2 editable decks / 16 layout types (not final style)",
}


def report(root:Path=ROOT)->dict:
    # Existing per-family verification also inspects real file signatures,
    # SVG editability, PDF MediaBox, PowerPoint native text/vector shapes,
    # SHA256 PNG previews and declared draft status.
    families = {
        "print_posters_and_price_signs": verify_print(root/"docs/design/technical-drafts"),
        "museum_and_office": verify_secondary(root/"docs/design/technical-drafts/secondary"),
        "digital_vk_and_merch": verify_digital(root/"docs/design/technical-drafts/digital-merch"),
    }
    expected={"svg":42,"pdf":26,"png":16,"pptx":2}
    paths=list((root/"docs/design/technical-drafts").rglob("TECH_*"))
    got=Counter(p.suffix.lower().lstrip(".") for p in paths if p.is_file())
    for ext,count in expected.items():
        if got[ext]!=count:
            raise ValueError(f"Unexpected technical {ext} count: {got[ext]}, expected {count}")
    targets={d.id for d in define()}
    if len(targets)!=113:
        raise ValueError("Canonical target inventory changed unexpectedly")
    categories=[]
    for ext,(tz,description,manual) in FINAL.items():
        for ref in tz.split(","):
            if ref not in (root/"docs/tz-audit/requirements.psv").read_text(encoding="utf-8"):
                raise ValueError("Missing original TZ reference "+ref)
        categories.append({
            "required_extension":ext,
            "tz_reference":tz,
            "final_artifact_description":description,
            "neutral_technical_sample":SUPPLIED.get(ext,"NONE"),
            "final_customer_approved_format": "NOT_PROVIDED",
            "native_edit_test": "REQUIRES_REAL_APPROVED_SOURCE_AND_TARGET_SOFTWARE",
            "manual_acceptance":manual,
        })
    return {
        "classification": "PREAWARD_TECHNICAL_DRAFT_COMPATIBILITY_ONLY",
        "approved_design_items":0,
        "final_source_files_accepted":0,
        "production_print_ready":False,
        "real_museum_brand_available":False,
        "target_design_items":len(targets),
        "technical_file_counts":{ext:int(got[ext]) for ext in expected},
        "family_structural_verification":"PASS_NOT_LEGAL_ACCEPTANCE",
        "family_checks":{
            "print":{
                "editable_svg_grids":families["print_posters_and_price_signs"]["neutral_svg_print_layouts"],
                "pptx_editable_slide_layouts":families["print_posters_and_price_signs"]["pptx_editable_slide_layouts"],
            },
            "museum_office":{
                "editable_svgs":families["museum_and_office"]["svg"],
                "physical_pdf_previews":families["museum_and_office"]["pdf_previews"],
            },
            "digital_merch":{
                "editable_svgs":families["digital_vk_and_merch"]["editable_svgs"],
                "png_preview_sha256_verified":families["digital_vk_and_merch"]["png_previews"],
            },
        },
        "formats":categories,
        "open_hard_gates":[
            "True editable AI/EPS/PSD/TIFF and legacy PPT files NOT created",
            "Actual approved SVG/PNG/PDF/PPTX not created despite technical examples",
            "Native Adobe and PowerPoint read-edit-save verification with customer's licensed software",
            "300dpi print raster at accepted physical dimensions; CMYK/Pantone, fonts, bleed, proof",
            "Customer-approved brand, media rights and real content; no placeholders",
            "Proof of originality and IP ownership chain; third-party notices",
            "Confirmed VK crop and actual product printing/die-cut specs",
            "Formal customer acceptance, signed rights act and real transfer to agreed media",
        ],
    }


def markdown(data:dict)->str:
    out=[
        "# MusBread — CP-33D technical format compatibility and real acceptance gaps","",
        "**Not proof of production delivery, Adobe editability, 300dpi artwork or rights transfer.**","",
        f"Verified technical sample files: {data['technical_file_counts']}.",
        f"Approved production design items: {data['approved_design_items']} / {data['target_design_items']}.",
        "",
        "| Final format | Source TZ | Technical prototype only | Actual approved source | Native/manual gate |",
        "|---|---|---|---|---|",
    ]
    for f in data["formats"]:
        out.append("| "+" | ".join([f["required_extension"],f["tz_reference"],
            f["neutral_technical_sample"],f["final_customer_approved_format"],
            f["manual_acceptance"]])+" |")
    out+=["","## Explicit hard blockers",""]
    out+=["- "+x for x in data["open_hard_gates"]]
    return "\n".join(out)+"\n"


def main()->int:
    p=argparse.ArgumentParser()
    p.add_argument("--root",type=Path,default=ROOT)
    p.add_argument("--json",type=Path)
    p.add_argument("--markdown",type=Path)
    p.add_argument("--verify-generated",action="store_true")
    opts=p.parse_args()
    data=report(opts.root)
    for path,content in ((opts.json,json.dumps(data,ensure_ascii=False,indent=2)+"\n"),
                         (opts.markdown,markdown(data))):
        if path:
            if opts.verify_generated:
                if not path.is_file() or path.read_text(encoding="utf-8")!=content:
                    raise ValueError("Generated format report missing/stale: "+str(path))
            else:
                path.parent.mkdir(parents=True,exist_ok=True)
                path.write_text(content,encoding="utf-8")
    print("FORMAT COMPATIBILITY GATE:",data["technical_file_counts"],
          "target designs",data["target_design_items"],
          "approved",data["approved_design_items"],"FORMAT_GATES_OPEN",len(data["open_hard_gates"]))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
