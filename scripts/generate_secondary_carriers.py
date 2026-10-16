#!/usr/bin/env python3
"""CP-31D: neutral editable technical geometry for museum and office carriers.

All dimensions EXCEPT A4 letterhead are preliminary examples, NOT specified
by the procurement. No names, employee PII, codes, prices or museum marks.
SVG has real editable paths/text; PDF is a vector preview, not CMYK artwork.
"""
from __future__ import annotations

import argparse
import json
import math
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from xml.etree import ElementTree
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs/design/technical-drafts/secondary"
STATUS = "TECHNICAL_DRAFT_ONLY"
SVG = "{http://www.w3.org/2000/svg}"
MB = "{https://musbread.local/technical-draft}"

@dataclass(frozen=True)
class Secondary:
    id: str
    tz: str
    label: str
    trim_mm: tuple[int, int]
    bleed_mm: int
    safe_mm: int
    requested_from_museum: str
    design: str
    dimensions_source: str

# The ONLY size here specified by any source is A4 for the conventional
# working letterhead. Even it is not a contractually stated letterhead size.
# Never confuse these provisional examples with a customer's specifications.
CARRIERS: tuple[Secondary, ...] = (
    Secondary("SIGN-IN","TZ-043","Вход на экспозицию",(300,150),3,12,
              "Габариты, схема движения, тексты указателя","direction","proposed"),
    Secondary("SIGN-OUT","TZ-044","Выход с экспозиции",(300,150),3,12,
              "Габариты, маршрут выхода и стрелки","direction","proposed"),
    Secondary("LABEL","TZ-045","Этикетка экспоната",(100,70),3,6,
              "Реальная этикетка и обязательные поля","label","proposed"),
    Secondary("ANNOTATION","TZ-046","Аннотация экспоната",(210,148),3,10,
              "Образец аннотации, предел знаков, шрифты","annotation","proposed"),
    Secondary("OFFICE-BLANK","TZ-047","Фирменный бланк",(210,297),3,12,
              "Официальное название, реквизиты, исходник логотипа","letterhead","A4_example"),
    Secondary("TICKET","TZ-048","Билет на экспозицию",(180,70),3,7,
              "Размер билета, места для маркировки, цены/категории","ticket","proposed"),
    Secondary("CARD-1","TZ-049","Визитка — горизонтальная",(90,50),3,5,
              "Официальные контакты; не передавать реальные ПДн до согласования","card_h","proposed"),
    Secondary("CARD-2","TZ-049","Визитка — вертикальная",(50,90),3,5,
              "Официальные контакты; не передавать реальные ПДн до согласования","card_v","proposed"),
    Secondary("BADGE-1","TZ-050","Бейдж — горизонтальный",(85,55),3,5,
              "Правила именных бейджей, обезличенный пример","badge_h","proposed"),
    Secondary("BADGE-2","TZ-050","Бейдж — вертикальный",(55,85),3,5,
              "Правила именных бейджей, обезличенный пример","badge_v","proposed"),
    Secondary("INVITATION","TZ-051","Приглашение",(148,210),3,10,
              "Сценарий приглашения, официальный текст","invitation","proposed"),
    Secondary("THANKS","TZ-052","Благодарность",(210,297),3,12,
              "Утверждённый текст, подпись и должность","thanks","A4_example"),
    Secondary("GREETING","TZ-053","Поздравительная открытка",(148,105),3,8,
              "Повод, цитата, двусторонняя печать?","greeting","proposed"),
)
EXPECTED={item.id for item in CARRIERS}

def px300(mm:int)->int:
    return math.ceil(mm * 300 / 25.4)

def geometry(item:Secondary)->dict:
    w,h=item.trim_mm
    b=item.bleed_mm
    s=item.safe_mm
    if w<=2*s+20 or h<=2*s+20 or b<0 or b>10 or s<4 or s>25:
        raise ValueError("Unsupported carrier geometry")
    return {
        **asdict(item),
        "full_artboard_mm":[w+2*b,h+2*b],
        "safe_box_mm":[b+s,b+s,w-2*s,h-2*s],
        "minimum_raster_pixels_for_future_print_300dpi":[px300(w+2*b),px300(h+2*b)],
        "status":STATUS,
    }

def make_svg(item:Secondary)->str:
    p=geometry(item)
    w,h=item.trim_mm
    b,s=item.bleed_mm,item.safe_mm
    aw,ah=p["full_artboard_mm"]
    x,y,sw,sh=p["safe_box_mm"]
    font=max(2.1,min(5,sw/40))
    label=escape(item.label)
    lines=[
        '<?xml version="1.0" encoding="utf-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:mb="https://musbread.local/technical-draft" '
        f'width="{aw}mm" height="{ah}mm" viewBox="0 0 {aw} {ah}" '
        f'mb:id="{item.id}" mb:tz="{item.tz}" mb:trim-width-mm="{w}" '
        f'mb:trim-height-mm="{h}" mb:bleed-mm="{b}" mb:safe-mm="{s}" '
        f'mb:dimensions-source="{item.dimensions_source}" mb:status="{STATUS}">',
        '<title>Технический шаблон: '+label+' (не согласован с заказчиком)</title>',
        '<desc>Все размеры кроме типового A4 — предварительные примеры, требуется согласование с музеем и типографией. Никаких персональных данных.</desc>',
        '<g id="editable-background"><rect width="100%" height="100%" fill="#ffffff"/></g>',
        f'<g id="guides-trim" stroke="#64748b" fill="none" stroke-width=".25">'
        f'<rect id="trim-guide" x="{b}" y="{b}" width="{w}" height="{h}"/></g>',
        f'<g id="guides-safe" stroke="#c2410c" stroke-width=".25" stroke-dasharray="2 2" fill="none">'
        f'<rect id="safe-guide" x="{x}" y="{y}" width="{sw}" height="{sh}"/></g>',
        f'<g id="draft-marker" font-family="Arial,sans-serif" fill="#9a3412">'
        f'<text id="draft-watermark" x="{x}" y="{y+3}" font-size="{max(1.9, font*.45)}">'
        f'ТЕХНИЧЕСКИЙ ШАБЛОН · НЕ УТВЕРЖДЕНО</text></g>',
        f'<g id="editable-content" font-family="Arial,sans-serif" fill="#1e293b">',
    ]
    def txt(id:str,xx:float,yy:float,st:str,scale:float=1.0,bold:bool=False):
        return (f'<text id="{id}" x="{xx:.2f}" y="{yy:.2f}" font-size="{font*scale:.2f}"'
                +(' font-weight="bold"' if bold else '')+'>'+escape(st)+'</text>')
    def rect(id:str,xx:float,yy:float,ww:float,hh:float,fill:str="#f8fafc"):
        return (f'<rect id="{id}" x="{xx:.2f}" y="{yy:.2f}" width="{ww:.2f}" '
                f'height="{hh:.2f}" fill="{fill}" stroke="#94a3b8" stroke-width=".35"/>')
    typ=item.design
    if typ=="direction":
        left=(item.id=="SIGN-IN")
        lines.append(txt("field-direction",x+sw*.07,y+sh*.56,"ВХОД" if left else "ВЫХОД",2.5,True))
        # Direction is intentionally a separate editable vector arrow.
        midx=x+sw*.79; midy=y+sh*.47
        if left:
            d=f"M{midx+18:.2f} {midy:.2f} H{midx-16:.2f} L{midx-7:.2f} {midy-10:.2f} M{midx-16:.2f} {midy:.2f} L{midx-7:.2f} {midy+10:.2f}"
        else:
            d=f"M{midx-18:.2f} {midy:.2f} H{midx+16:.2f} L{midx+7:.2f} {midy-10:.2f} M{midx+16:.2f} {midy:.2f} L{midx+7:.2f} {midy+10:.2f}"
        lines.append(f'<path id="editable-direction-arrow" d="{d}" fill="none" stroke="#1e293b" stroke-width="2.8"/>')
        lines.append(txt("field-subtitle",x+sw*.08,y+sh*.8,"[УТОЧНИТЬ МАРШРУТ У МУЗЕЯ]",.7))
    elif typ=="label":
        lines += [
            txt("field-inventory",x,y+sh*.19,"ИНВ. № [0000]",.85),
            txt("field-title",x,y+sh*.45,"[НАИМЕНОВАНИЕ]",1.15,True),
            txt("field-author",x,y+sh*.63,"[АВТОР / МАТЕРИАЛ]",.77),
            txt("field-period",x,y+sh*.80,"[ДАТИРОВКА / КОЛЛЕКЦИЯ]",.7),
        ]
    elif typ=="annotation":
        lines += [
            txt("field-heading",x,y+sh*.17,"[ЗАГОЛОВОК АННОТАЦИИ]",1.45,True),
            rect("image-placeholder",x+sw*.65,y+sh*.26,sw*.33,sh*.52),
            txt("field-body1",x,y+sh*.33,"[ТЕКСТ МУЗЕЯ · СТРОКА 1]",.8),
            txt("field-body2",x,y+sh*.47,"[ТЕКСТ МУЗЕЯ · СТРОКА 2]",.8),
            txt("field-body3",x,y+sh*.61,"[ТЕКСТ МУЗЕЯ · СТРОКА 3]",.8),
            txt("field-caption",x,y+sh*.86,"[ИСТОЧНИК / ПРАВА]",.7),
        ]
    elif typ=="letterhead":
        lines += [
            rect("logo-placeholder",x,y+sh*.09,sw*.19,sh*.09),
            txt("field-org",x+sw*.25,y+sh*.145,"[ОФИЦИАЛЬНОЕ НАИМЕНОВАНИЕ]",.9,True),
            txt("field-contacts",x,y+sh*.23,"[АДРЕС И РЕКВИЗИТЫ]",.8),
            txt("field-number",x,y+sh*.34,"Исх. № [____] от [________]",.8),
            txt("field-addressee",x+sw*.53,y+sh*.43,"[КУДА / КОМУ]",.8),
            txt("field-subject",x,y+sh*.53,"[ТЕМА ПИСЬМА]",1.1,True),
            txt("field-body",x,y+sh*.64,"[ОСНОВНОЙ ТЕКСТ: ПРИМЕР ПОЛЯ]",.8),
            txt("field-signature",x,y+sh*.87,"[ПОДПИСЬ / ДОЛЖНОСТЬ]",.8),
        ]
    elif typ=="ticket":
        lines += [
            txt("field-type",x,y+sh*.28,"БИЛЕТ НА ЭКСПОЗИЦИЮ",1.15,True),
            txt("field-category",x,y+sh*.52,"[КАТЕГОРИЯ / ДАТА / ВРЕМЯ]",.8),
            txt("field-serial",x,y+sh*.76,"[СЕРИЯ / НОМЕР · ТОЛЬКО ПРИМЕР]",.7),
            rect("qr-placeholder",x+sw*.80,y+sh*.15,sw*.18,sh*.65),
        ]
    elif typ in ("card_h","card_v"):
        v=typ=="card_v"
        lines += [
            rect("logo-placeholder",x,y+sh*.16,sw*(.28 if not v else .45),sh*.17),
            txt("field-person",x,y+sh*(.47 if not v else .48),"[ИМЯ / БЕЗ ПДН]",1 if not v else .8,True),
            txt("field-role",x,y+sh*.63,"[ДОЛЖНОСТЬ]",.8),
            txt("field-contact",x,y+sh*.78,"[КОНТАКТ]",.7),
        ]
    elif typ in ("badge_h","badge_v"):
        v=typ=="badge_v"
        lines += [
            rect("logo-placeholder",x,y+sh*.16,sw*.26,sh*.17),
            txt("field-person",x,y+sh*.55,"[СОТРУДНИК]",1 if not v else .8,True),
            txt("field-role",x,y+sh*.76,"[ДОЛЖНОСТЬ]",.8),
        ]
    else:
        heading={"invitation":"ПРИГЛАШЕНИЕ","thanks":"БЛАГОДАРНОСТЬ","greeting":"ПОЗДРАВЛЕНИЕ"}[typ]
        lines += [
            rect("logo-placeholder",x,y+sh*.11,sw*.2,sh*.10),
            txt("field-title",x,y+sh*.39,heading,1.5,True),
            txt("field-recipient",x,y+sh*.56,"[АДРЕСАТ / ОБРАЩЕНИЕ]",.84),
            txt("field-body",x,y+sh*.72,"[СОГЛАСОВАННЫЙ ТЕКСТ]",.8),
            txt("field-signature",x,y+sh*.87,"[ДАТА / ПОДПИСЬ / МЕСТО]",.65),
        ]
    lines.append("</g>")
    # Crops inside the bleed stripe rather than the finished piece.
    paths=[]
    if b>0:
        for xx in (b,b+w):
            paths.append(f'M{xx} .5 V{b-.5} M{xx} {b+h+.5} V{ah-.5}')
        for yy in (b,b+h):
            paths.append(f'M.5 {yy} H{b-.5} M{b+w+.5} {yy} H{aw-.5}')
    lines.append('<g id="crop-marks" fill="none" stroke="#111827" stroke-width=".22">'
                 +''.join(f'<path d="{d}"/>' for d in paths)+'</g>')
    lines.append("</svg>")
    return "\n".join(lines)+"\n"

def manifest()->dict:
    return {
        "status":"ONLY_PREAWARD_TECHNICAL_DRAFTS_NOT_MUSEUM_APPROVED",
        "source":"TZ-043..053 obligate types and counts, NOT carrier dimensions",
        "museum_personal_data_used":False,
        "actual_customer_approved":0,
        "carriers":[geometry(s) for s in CARRIERS],
    }

def generate(directory:Path,render_pdf:bool=False)->None:
    directory.mkdir(parents=True,exist_ok=True)
    for s in CARRIERS:
        source=directory/f"TECH_{s.id}.svg"
        source.write_text(make_svg(s),encoding="utf-8")
        if render_pdf:
            subprocess.run(["rsvg-convert","--format","pdf","--output",str(source.with_suffix(".pdf")),str(source)],
                           check=True,capture_output=True,timeout=12)
    (directory/"SECONDARY_MANIFEST.json").write_text(
        json.dumps(manifest(),ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

def verify(directory:Path)->dict:
    from pypdf import PdfReader
    ids={s.id for s in CARRIERS}
    if ids!={"SIGN-IN","SIGN-OUT","LABEL","ANNOTATION","OFFICE-BLANK","TICKET",
              "CARD-1","CARD-2","BADGE-1","BADGE-2","INVITATION","THANKS","GREETING"}:
        raise ValueError("Missing mandatory original TZ secondary carrier")
    mfile=directory/"SECONDARY_MANIFEST.json"
    if not mfile.is_file() or mfile.read_text(encoding="utf8")!=json.dumps(
            manifest(),ensure_ascii=False,indent=2)+"\n":
        raise ValueError("Secondary manifest missing/stale/altered")
    result={}
    for s in CARRIERS:
        source=directory/f"TECH_{s.id}.svg"
        pdf=source.with_suffix(".pdf")
        if not source.is_file() or not pdf.is_file():
            raise ValueError("Missing technical carrier: "+s.id)
        if source.read_text(encoding="utf8")!=make_svg(s):
            raise ValueError("Technical SVG changed, regenerate through source: "+s.id)
        root=ElementTree.parse(source).getroot()
        names={element.attrib.get("id") for element in root.iter()}
        if not {"trim-guide","safe-guide","editable-content","draft-watermark","crop-marks"}.issubset(names):
            raise ValueError("Missing distinct editable SVG guides/fields")
        if root.attrib.get(MB+"status")!=STATUS:
            raise ValueError("Technical status removed")
        for marker in ("field-person","field-role"):
            if s.id.startswith(("BADGE","CARD")) and marker not in names:
                raise ValueError("Missing editable employee placeholder")
        if s.design=="direction" and "editable-direction-arrow" not in names:
            raise ValueError("Direction arrow not editable")
        pages=PdfReader(str(pdf)).pages
        if len(pages)!=1:
            raise ValueError("Only one PDF preview expected")
        ww,hh=geometry(s)["full_artboard_mm"]
        pdfw=float(pages[0].mediabox.width)*25.4/72
        pdfh=float(pages[0].mediabox.height)*25.4/72
        if abs(ww-pdfw)>.15 or abs(hh-pdfh)>.15:
            raise ValueError("PDF preview physical geometry mismatch for "+s.id)
        result[s.id]={"paper_trim_mm":s.trim_mm,"pdf_full_mm":[round(pdfw,2),round(pdfh,2)],
                      "editable_text_fields":len([n for n in root.iter() if n.tag==SVG+"text"]),
                      "status":STATUS}
    return {"svg":len(result),"pdf_previews":len(result),"approved":0,
            "dimensions_approved":False,"results":result}

def main()->int:
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",type=Path,default=OUTPUT)
    parser.add_argument("--verify",action="store_true")
    args=parser.parse_args()
    if not args.verify:
        generate(args.output,render_pdf=True)
    print("SECONDARY TECHNICAL CARRIERS:",json.dumps(verify(args.output),ensure_ascii=False))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
