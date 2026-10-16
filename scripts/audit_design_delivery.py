#!/usr/bin/env python3
"""TZ-grounded design deliverable checklist and binary-format plausibility gate.

This pre-award audit cannot prove editability, originality, licenses, print quality,
registration eligibility, customer approval, ownership, or actual handover.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import re
import struct
import zipfile
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[1]
MAGIC_OLE = bytes.fromhex("D0CF11E0A1B11AE1")
DESIGN_GROUP = {"concept", "brand", "web", "vk", "print", "museum", "office", "slides", "merch", "format", "handover"}
PHASE = {"before_interview", "after_interview", "after_brand_approval", "after_contract"}
SOURCE_IDS = set()


@dataclass(frozen=True)
class Target:
    id: str
    tz: str
    group: str
    name: str
    variant: str
    formats: str
    input: str
    phase: str
    gate: str


def define() -> list[Target]:
    data: list[Target] = []

    def row(id: str, tz: str, group: str, name: str, variant: str,
            formats: str, input: str, phase: str, gate: str) -> None:
        data.append(Target(id, tz, group, name, variant, formats, input, phase, gate))

    # Concepts must be THREE genuinely different, five pages or more each.
    for n in (1, 2, 3):
        row(f"C{n:02d}-PDF", "TZ-007,TZ-013", "concept", f"Concept {n}", "at least 5 pages",
            ".pdf", "Interview conclusions; brand boundaries; legal names", "after_interview",
            "5+ substantive pages, distinct from other directions, PDF opened, customer received")
        for code, tz, title in (
            ("LOGO", "TZ-008", "Logo"),
            ("FONT", "TZ-009", "Typeface"),
            ("COLOR", "TZ-010", "Color palette"),
            ("HOME", "TZ-011", "Homepage example"),
            ("MERCH", "TZ-012", "Merch mockups")):
            row(f"C{n:02d}-{code}", tz, "concept", f"Concept {n} / {title}", "in concept PDF",
                ".pdf", "Interview, references and approved input assets", "after_interview",
                "Evidence of actual content on concept pages, not just heading/template")

    for id, tz, name, variant, fmt, request in [
        ("B-LOGO-RU", "TZ-020", "Official RU logo", "master", ".ai|.eps|.svg", "Official RU title"),
        ("B-LOGO-EN", "TZ-020", "Official EN logo", "master", ".ai|.eps|.svg", "Approved EN title"),
        ("B-LOGO-H", "TZ-021", "Horizontal logo layout", "horizontal", ".ai|.eps|.svg", "Selected concept"),
        ("B-LOGO-V", "TZ-021", "Vertical logo layout", "vertical", ".ai|.eps|.svg", "Selected concept"),
    ]:
        row(id,tz,"brand",name,variant,fmt,request,"after_brand_approval","Actual editable source, optical/physical checks, written approval")
    for code, label in [("COLOR","full color"),("BW","monochrome"),("CONTRAST","high contrast")]:
        row("B-LOGO-"+code, "TZ-022", "brand", "Logo treatment", label, ".svg|.pdf",
            "Selected identity", "after_brand_approval", "Contrast/readability plus editor-approved source")
    for id,tz,name,variant,fmt,inp in [
        ("B-USE","TZ-023","Logo usage rules","allowed/prohibited",".pdf","Selected logo"),
        ("B-TYPE","TZ-024,TZ-025","Type scale & license register","H1/H2/body, free/open licenses",".pdf","Typeface files and license"),
        ("B-COLORS","TZ-026","Colors","RGB/CMYK/Pantone/HEX",".pdf","Approved colors"),
        ("B-GRADIENTS","TZ-027","Gradients","at least 2",".svg|.pdf","Approved colors"),
        ("B-ICONS","TZ-028","Pictograms","at least 10",".svg|.pdf","Navigation uses"),
        ("B-PATTERNS","TZ-029","Patterns","at least 3 distinct styles",".svg|.pdf","Selected concept"),
        ("B-GRID","TZ-030","Layout grid rules","digital and print",".pdf","Approved identity"),
        ("B-REG","TZ-018,TZ-019","Registration/originality evidence","legal review, not registration guarantee",".pdf","Names, rights and lawyer"),
    ]:
        row(id,tz,"brand",name,variant,fmt,inp,"after_brand_approval",
            "Real specification, not a blank outline; license/registration checks manual")
    row("WEB-HOME","TZ-032","web","Homepage branded mockup","desktop/mobile",".svg|.png|.pdf","Approved site content and brand",
        "after_brand_approval","Editable design and matching approved public layout")
    row("WEB-INNER","TZ-033","web","Internal page branded mockup","desktop/mobile",".svg|.png|.pdf","Approved internal content and brand",
        "after_brand_approval","Editable design and matching approved public layout")
    row("WEB-POSTER","TZ-034","web","Digital event material template","editable",".svg|.png|.pdf","Approved categories and brand",
        "after_brand_approval","Editable template and realistic approved example")
    row("VK-AVATAR","TZ-035","vk","VK community avatar","separate image",".png|.jpg|.svg",
        "Official VK account/dimensions","after_brand_approval","File and display crop verified")
    row("VK-COVER","TZ-036","vk","VK profile cover","separate image",".png|.jpg|.svg",
        "Official VK account/dimensions","after_brand_approval","File and display crop verified")
    for n in range(1,5):
        row(f"VK-RUBRIC-{n}","TZ-037","vk","VK category poster",f"distinct rubric {n}",".png|.jpg|.svg",
            "Four approved editorial rubric names","after_brand_approval","Four visually distinguished templates")
    for tag,tz,label,sizes,customer in [
        ("TEMP","TZ-038","Temporary exhibition",["A3","A2"],"Exhibition information and print specification"),
        ("CHILD","TZ-039","Children's workshop",["A4","A3","A2"],"Workshop copy and print specification"),
        ("SCIENCE","TZ-040","Scientific event",["A4","A3","A2"],"Scientific event copy and print specification"),
        ("LEISURE","TZ-041","Entertaining event",["A4","A3","A2"],"Event copy and print specification"),
    ]:
        for paper in sizes:
            row(f"POSTER-{tag}-{paper}",tz,"print",label,paper,".pdf|.ai|.eps|.svg|.tiff",
                customer,"after_brand_approval","Separate approved dimension, bleed and proof for print; >=300 dpi for raster")
    for size in ("A4","A3"):
        row(f"PRICE-HOURS-{size}","TZ-042","museum","Price & hours sign",size,".pdf|.ai|.svg",
            "Official price list, accessible hours, installation dimensions","after_brand_approval",
            "Checked official details, separate size, mockup and printable master")
    for id,tz,label,inp in [
        ("SIGN-IN","TZ-043","Exposition entrance direction","Floorplan/entrance and sign size"),
        ("SIGN-OUT","TZ-044","Exposition exit direction","Visitor exit route and sign size"),
        ("LABEL","TZ-045","Exhibit label","Approved label fields and real sample"),
        ("ANNOTATION","TZ-046","Museum annotation","Approved annotation fields and sample"),
    ]:
        row(id,tz,"museum",label,"independent editable template",".svg|.ai|.pdf",
            inp,"after_brand_approval","Actual copy/arrow and legible printable master")
    for id,tz,label,variant,inp in [
        ("OFFICE-BLANK","TZ-047","Letterhead","editable","Official requisites"),
        ("TICKET","TZ-048","Exposition entrance ticket","print","Tariffs, ticket dimensions and operator"),
        ("CARD-1","TZ-049","Business card","variation 1","Approved official contacts"),
        ("CARD-2","TZ-049","Business card","variation 2","Approved official contacts"),
        ("BADGE-1","TZ-050","Staff badge","variation 1","Privacy-safe fields/sample"),
        ("BADGE-2","TZ-050","Staff badge","variation 2","Privacy-safe fields/sample"),
        ("INVITATION","TZ-051","Invitation","editable","Categories and approved copy"),
        ("THANKS","TZ-052","Thank-you letter","editable","Approved copy"),
        ("GREETING","TZ-053","Greeting card","editable","Approved occasion/copy"),
    ]:
        row(id,tz,"office",label,variant,".pdf|.svg|.ai",
            inp,"after_brand_approval","Printable and editable master, actual approved text, rights")
    # TZ-054..058 require >= 8 classes of slides in TWO aspect ratios.
    # This eight-type taxonomy is a proposed minimal implementation, not
    # a list of eight named templates from the tender itself.
    slide_types=[
        ("TITLE","Title", "TZ-054"),
        ("CLOSING","Closing", "TZ-054"),
        ("TEXT","Text-heavy", "TZ-055"),
        ("IMAGE","Image-heavy", "TZ-055"),
        ("MIXED","Text and image", "TZ-055"),
        ("FOUR","4 text blocks", "TZ-056"),
        ("SIX","6 text blocks", "TZ-056"),
        ("DATA","Data/table/diagram", "TZ-055"),
    ]
    for ratio in ("4x3","16x9"):
        for code,title,tz in slide_types:
            row(f"PPT-{ratio}-{code}",tz+",TZ-057,TZ-058","slides",f"PowerPoint / {title}",ratio,
                ".ppt|.pptx","Selected brand, real sample content, fonts",
                "after_brand_approval","Editable slide master, rendered/tested in native presentation app")
    for code,tz,label in [
        ("NOTEPAD","TZ-059","Notepad"),("VEST","TZ-059","Vest"),
        ("TSHIRT","TZ-060","T-shirt"),("STAMP","TZ-060","Stamp"),
        ("STICKERS","TZ-060","Sticker pack"),("CALENDAR","TZ-061","Calendar"),
        ("POSTCARD","TZ-061","Postcard"),("THERMOMUG","TZ-061","Thermal mug"),
        ("SHOPPER","TZ-061","Shopper tote bag")
    ]:
        row("MERCH-"+code,tz,"merch",label,"actual visual mockup",".png|.jpg|.pdf",
            "Museum merchandising preferences and product specifications",
            "after_brand_approval","Approved real mockup for this distinct application")
    for id,tz,label,fmt,inp in [
        ("SOURCE-AI","TZ-066,TZ-071","Adobe Illustrator editable source",".ai","Licensed graphics and actual editable output"),
        ("SOURCE-EPS","TZ-066,TZ-071","PostScript vector source",".eps","Vector graphics"),
        ("SOURCE-SVG","TZ-066,TZ-071","Scalable vector source",".svg","Approved vectors"),
        ("SOURCE-PSD","TZ-067","Layered raster master",".psd","Approved layered raster"),
        ("SOURCE-TIFF","TZ-067,TZ-068","Raster print master >=300 dpi",".tiff","Exact output size and raster source"),
        ("VIEW-PDF","TZ-069","Viewing/print PDF",".pdf","Approved assets"),
        ("VIEW-JPG","TZ-069,TZ-071","Viewing JPEG",".jpg","Approved assets"),
        ("VIEW-PNG","TZ-069,TZ-071","Viewing PNG",".png","Approved assets"),
        ("SOURCE-PPT","TZ-070","Legacy editable slideshow",".ppt","Finished editable presentation"),
        ("SOURCE-PPTX","TZ-070","Editable OpenXML slideshow",".pptx","Finished editable presentation"),
    ]:
        row(id,tz,"format",label,"actual target format",fmt,inp,
            "after_brand_approval","Format plausibility PLUS manual open/edit and license inspection")
    for id,tz,label,variant,inp,phase in [
        ("CONCEPT-EMAIL","TZ-014","Submit 3 PDF concepts to museum","acknowledged email and archive","Official museum email","after_interview"),
        ("CONCEPT-DEMO","TZ-015","Present concepts within 2 business days","delivery/receipt timestamps","Museum decision makers and dates","after_interview"),
        ("BRAND-APPROVAL","TZ-016","Written selection of identity direction","signed decision","Museum authorized decision maker","after_interview"),
        ("BRAND-REVISION","TZ-062","Change log max 3 revision rounds","three or fewer iterations","Museum written feedback","after_brand_approval"),
        ("CARRIERS-DEMO","TZ-031,TZ-063","Show all approved carriers","video meeting/on-site record","Museum decision maker and presentation time","after_brand_approval"),
    ]:
        row(id,tz,"handover",label,variant,"procedure",inp,phase,
            "Evidence of actual presentation/delivery, never automatically approved")
    for id,tz,label,variant,inp in [
        ("DISK-CLOUD","TZ-064,TZ-325","Yandex.Disk folder","restricted share","Receiving account and access policy"),
        ("DISK-HDD","TZ-065,TZ-305,TZ-325","External hard disk","independent checksum","Recipient, filesystem and HDD agreement"),
        ("DOC-PAPER","TZ-304,TZ-325","Paper documentation","one paper copy","Recipient/signing route"),
        ("ACT-RIGHTS","TZ-318,TZ-321,TZ-324","Rights transfer act","two originals / approved e-sign","Exact contract, museum requisites"),
        ("DOC-CODE","TZ-306","Complete versioned source code","Git SHA and LICENSE manifest","Contract signing/delivery route"),
    ]:
        row(id,tz,"handover",label,variant,"procedure",inp,"after_contract",
            "Authorized museum receiver, content inventory, checksum and signed acknowledgement")
    return data


def tender_requirements(root: Path) -> dict[str, dict[str,str]]:
    with (root / "docs/tz-audit/requirements.psv").open(newline="", encoding="utf-8") as f:
        return {x["ID"]:x for x in csv.DictReader(f,delimiter="^")}


def check_design_catalog(rows: list[Target], requirements: dict[str,dict]) -> None:
    ids=[x.id for x in rows]
    if len(set(ids))!=len(ids):
        raise ValueError("Duplicate design delivery ID")
    if len(rows)<90:
        raise ValueError("Design handover registry unexpectedly incomplete")
    for row in rows:
        if row.group not in DESIGN_GROUP or row.phase not in PHASE:
            raise ValueError("Invalid grouping or phase")
        if not row.name.strip() or not row.input.strip() or not row.gate.strip():
            raise ValueError("Missing name/customer input/gate")
        for tz in row.tz.split(","):
            if tz not in requirements:
                raise ValueError(f"Missing original tender requirement {tz} for {row.id}")
    byid=set(ids)
    for needed in ["C01-PDF","C02-PDF","C03-PDF","VK-RUBRIC-4",
                   "POSTER-CHILD-A2","POSTER-SCIENCE-A3","POSTER-LEISURE-A4",
                   "PPT-4x3-FOUR","PPT-16x9-SIX","SOURCE-AI","SOURCE-PPT","SOURCE-PPTX",
                   "CARD-1","CARD-2","BADGE-1","BADGE-2","DISK-HDD","ACT-RIGHTS"]:
        if needed not in byid:
            raise ValueError("Required distinct variant is missing: "+needed)
    if sum(row.id.startswith("PPT-") for row in rows)!=16:
        raise ValueError("Need eight proposed slide types in two aspect ratios")
    if sum(row.id.startswith("POSTER-") for row in rows)!=11:
        raise ValueError("Original TZ requires eleven individual size-specific event posters")


def plausible_format(path: Path, ext: str) -> tuple[bool,str]:
    """Plausibility check only; no proof of editability or quality."""
    if not path.is_file() or path.is_symlink():
        return False,"file missing or unsafe link"
    if path.stat().st_size==0 or path.stat().st_size>40_000_000:
        return False,"file empty or oversize"
    with path.open("rb") as f:
        data=f.read(min(128 * 1024,path.stat().st_size))
    if ext==".pdf":
        return data.startswith(b"%PDF-"),"PDF magic"
    if ext in {".jpg",".jpeg"}:
        return data.startswith(b"\xff\xd8\xff"),"JPEG magic"
    if ext==".png":
        return data.startswith(b"\x89PNG\r\n\x1a\n"),"PNG magic"
    if ext in {".tif",".tiff"}:
        return data.startswith((b"II*\x00",b"MM\x00*")),"TIFF magic (DPI must be checked separately)"
    if ext==".psd":
        return data.startswith(b"8BPS\x00\x01"),"PSD magic (layers/editability not verified)"
    if ext==".eps":
        return data.startswith(b"%!PS-Adobe") or data.startswith(bytes.fromhex("C5D0D3C6")), "EPS magic"
    if ext==".ai":
        return data.startswith(b"%PDF-") or data.startswith(b"%!PS-Adobe"),"AI may be PDF/PS compatible; native editability NOT verified"
    if ext==".svg":
        try:
            tree=ElementTree.fromstring(path.read_text(encoding="utf8"))
            return tree.tag=="{http://www.w3.org/2000/svg}svg","SVG XML root"
        except (UnicodeError,ElementTree.ParseError):
            return False,"Invalid SVG XML"
    if ext==".ppt":
        return data.startswith(MAGIC_OLE),"OLE2 magic; PowerPoint editability NOT verified"
    if ext==".pptx":
        try:
            with zipfile.ZipFile(path) as z:
                names=set(z.namelist())
                return {"[Content_Types].xml","ppt/presentation.xml"}.issubset(names), "PPTX package structure"
        except (OSError,zipfile.BadZipFile):
            return False,"Invalid PPTX container"
    return False,"No format validator for "+ext


def proof_map(root:Path) -> dict[str,dict[str,str]]:
    p=root/"docs/handoff/DESIGN_EVIDENCE.csv"
    if not p.is_file():
        return {}
    with p.open(newline="",encoding="utf8") as f:
        entries=list(csv.DictReader(f))
    if any("id" not in x or "path" not in x for x in entries):
        raise ValueError("Invalid evidence register header")
    ids=[x["id"] for x in entries]
    if len(ids)!=len(set(ids)):
        raise ValueError("Duplicate evidence ID")
    return {x["id"]:x for x in entries}


def inventory(root:Path)->tuple[list[dict[str,str]],dict]:
    rows=define()
    req=tender_requirements(root)
    check_design_catalog(rows,req)
    evidence=proof_map(root)
    unknown=set(evidence)-{x.id for x in rows}
    if unknown:
        raise ValueError("Evidence references unknown target IDs: "+",".join(sorted(unknown)))
    result=[]
    for row in rows:
        entry=asdict(row)
        ref=evidence.get(row.id,{})
        source=ref.get("path","").strip()
        notes=ref.get("notes","").strip()
        claimed=ref.get("museum_approval","").strip().lower()
        if claimed not in {"","no","pending"}:
            raise ValueError("Museum approval MUST NOT be asserted automatically in this pre-award register")
        entry["path"]=source
        entry["notes"]=notes
        entry["status"]="MISSING_CUSTOMER_APPROVED_RESULT"
        entry["format_check"]="NOT_CHECKED"
        if source:
            p=Path(source)
            if "technical-drafts" in p.parts or p.name.startswith("TECH_"):
                raise ValueError("Neutral technical drafts cannot be design-delivery evidence: "+source)
            if p.is_absolute() or ".." in p.parts or not source.startswith("docs/"):
                raise ValueError("Unsafe or private evidence path: "+source)
            full=(root/p).resolve()
            if not full.is_relative_to(root.resolve()):
                raise ValueError("Evidence escapes repository")
            suffix=full.suffix.lower()
            accepted=row.formats.split("|") if row.formats != "procedure" else [".md", ".pdf", ".txt"]
            if suffix not in accepted:
                entry["status"]="INVALID_FORMAT"
                entry["format_check"]="wrong extension"
            else:
                if row.formats == "procedure" and suffix in (".md", ".txt"):
                    ok=full.is_file() and not full.is_symlink() and 40<=full.stat().st_size<=50_000
                    detail="Procedural note exists; not museum acceptance"
                else:
                    ok,detail=plausible_format(full,suffix)
                entry["status"]="FORMAT_PLAUSIBLE_NOT_APPROVED" if ok else "INVALID_FORMAT"
                entry["format_check"]=detail if ok else "INVALID: "+detail
        result.append(entry)
    stats=Counter(x["status"] for x in result)
    summary={
        "targets":len(rows),
        "concept_pdfs":sum(x.id.startswith("C") and x.id.endswith("-PDF") for x in rows),
        "posters":sum(x.id.startswith("POSTER-") for x in rows),
        "ppt_slide_variants":sum(x.id.startswith("PPT-") for x in rows),
        "vk_rubrics":sum(x.id.startswith("VK-RUBRIC-") for x in rows),
        "merch_examples":sum(x.id.startswith("MERCH-") for x in rows),
        "format_plausible":stats["FORMAT_PLAUSIBLE_NOT_APPROVED"],
        "missing":stats["MISSING_CUSTOMER_APPROVED_RESULT"],
        "invalid_format":stats["INVALID_FORMAT"],
        "customer_approved":0,
        "rights_transferred":False,
    }
    return result,summary


def as_markdown(rows:list[dict[str,str]],s:dict)->str:
    out=[
        "# MusBread — detailed pre-handover design/format register",
        "",
        "**Internal target inventory only. Empty format slots mean no approved design file exists.**",
        "Do not substitute the three five-page concept PDF templates for genuine concepts.",
        "Format signatures do not prove editability, native app compatibility, fonts, licenses or customer acceptance.",
        "",
        f"Target positions: **{s['targets']}**; concept PDF: {s['concept_pdfs']}; poster-size variants: {s['posters']}; "
        f"slide type×ratio: {s['ppt_slide_variants']}; VK rubrics: {s['vk_rubrics']}; merch examples: {s['merch_examples']}.",
        f"Missing or not approved: {s['missing']}; plausible files needing manual verification: {s['format_plausible']}; "
        f"invalid formats: {s['invalid_format']}; museum-approved: **0**.",
        "",
        "| ID | TZ | Deliverable | Variant | Expected formats | Status | Museum input |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        values=[r["id"],r["tz"],r["name"],r["variant"],r["formats"],r["status"],r["input"]]
        out.append("| "+" | ".join(x.replace("|"," / ").replace("\n"," ") for x in values)+" |")
    out += [
        "",
        "## Acceptance gates still requiring human signatures/evidence",
        "",
        "- Concept presentation after interview and written approval of selected direction.",
        "- Originality, registerability under referenced regulation, open font licenses and ownership chain.",
        "- Native-editor open/edit tests for Adobe AI/EPS/PSD, vector SVG, real editable PPT/PPTX; 300 dpi/bleed at chosen real print sizes.",
        "- Photos, text, tariffs, ticket specs, entrance/exit plan, official company details and rubrics supplied by museum.",
        "- Yandex.Disk folder, identical external HDD content, checksums after copying and physically delivered paper set.",
        "- Rights act using original museum Appendix 1, two originals in Russian, only after actual fulfillment.",
        "",
        "Results marked FORMAT_PLAUSIBLE_NOT_APPROVED mean a binary signature matched but **not** that the museum approved the result.",
    ]
    return "\n".join(out)+"\n"


def request_markdown(rows:list[dict[str,str]], requirements:dict[str,dict[str,str]])->str:
    out=[
        "# MusBread — concrete requests to the museum after the interview",
        "",
        "**Draft questions only, not sent.** They derive from TZ source IDs cited for each handover slot.",
        "Arrange formal approvals with a named decision maker. Do not request confidential login details by ordinary email.",
        "",
        "| Priority | Museum input/confirmation | Linked original clauses | Deliverable positions |",
        "|---|---|---|---:|",
    ]
    groups:dict[str,list[dict]]={}
    for row in rows:
        groups.setdefault(row["input"],[]).append(row)
    for name,items in sorted(groups.items(),key=lambda q:-len(q[1])):
        refs=sorted({tz for x in items for tz in x["tz"].split(",")})
        priority="before branding" if any(x["phase"]=="after_interview" for x in items) else "during interview / approval"
        out.append(f"| {priority} | {name} | {', '.join(refs)} | {len(items)} |")
    out += [
        "",
        "## Workshop questions for the museum",
        "",
        "1. Confirm full statutory name in Russian and approved English rendering; decision maker and timeline.",
        "2. Approve precise list of event types, four VK rubrics, print bleed/trim sizes and physical placements.",
        "3. Provide official price/hours, exhibition plan, labels, ticket dimensions and permitted example content.",
        "4. Confirm fonts and photo rights and what originals may be adapted versus must remain unchanged.",
        "5. Agree which editable software/version is supported (Illustrator, Photoshop, PowerPoint), and how to test .ppt and .ai.",
        "6. Approve HDD recipient/filesystem, private Yandex.Disk transfer method and paper/signing procedure.",
        "7. Confirm whether original Appendix 1 rights act requires exactly two paper originals or approved electronic equivalent.",
        "8. Provide formal written sign-off after concepts, after revision rounds and before final deliverables.",
        "",
        "No design was asserted completed merely because a template or preview exists in Git.",
    ]
    return "\n".join(out)+"\n"


def csv_content(rows:list[dict])->str:
    content=io.StringIO(newline="")
    writer=csv.DictWriter(content,fieldnames=list(rows[0]),lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return content.getvalue()


def write_csv(p:Path,rows:list[dict])->None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(csv_content(rows),encoding="utf-8")


def require_matching_report(path:Path,expected:str)->None:
    if not path.is_file() or path.read_bytes()!=expected.encode("utf-8"):
        raise ValueError("Generated design handover report is missing or stale: "+str(path))


def main()->int:
    a=argparse.ArgumentParser()
    a.add_argument("--root",type=Path,default=ROOT)
    a.add_argument("--csv",type=Path)
    a.add_argument("--markdown",type=Path)
    a.add_argument("--requests",type=Path)
    a.add_argument("--json",type=Path)
    a.add_argument("--check",action="store_true", help="Fail on invalid format/path or catalog inconsistency, not missing museum-approved files")
    a.add_argument("--verify-generated",action="store_true",help="Reject stale CSV/Markdown reports without modifying them")
    args=a.parse_args()
    rows,summary=inventory(args.root)
    reports=[
        (args.csv, csv_content(rows)),
        (args.markdown, as_markdown(rows,summary)),
        (args.requests, request_markdown(rows,tender_requirements(args.root))),
    ]
    for path,content in reports:
        if path is None:
            continue
        if args.verify_generated:
            require_matching_report(path,content)
        else:
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text(content,encoding="utf-8")
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps({"status":"PREAWARD_UNAPPROVED", "summary":summary,"positions":rows},
                ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("DESIGN/HANDOFF PREAWARD INVENTORY:",summary)
    return int(args.check and summary["invalid_format"]>0)


if __name__=="__main__":
    raise SystemExit(main())
