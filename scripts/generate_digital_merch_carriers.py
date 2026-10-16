#!/usr/bin/env python3
"""CP-32D — reproducible neutral *digital previews*, not approved branding.

Editable SVG geometry + independent PNG previews for TZ-034..037 and TZ-059..061.
All canvas pixels are provisional wireframe canvases, never claimed VK specs or
manufacturing dimensions. Mockups contain no actual logo, copyright art or PII.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from xml.etree import ElementTree
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs/design/technical-drafts/digital-merch"
TZ_NS = "https://musbread.local/technical-draft"
SVG_NS = "http://www.w3.org/2000/svg"
STATUS = "TECHNICAL_DRAFT_ONLY"
TECH_NOTE = "ВИЗУАЛИЗАЦИЯ / ЧЕРНОВИК — НЕ УТВЕРЖДЕНО"


@dataclass(frozen=True)
class Draft:
    id: str
    tz: str
    title: str
    category: str
    canvas_px: tuple[int,int]
    kind: str
    inputs: str


DRAFTS = (
    Draft("WEB-POSTER","TZ-034","Цифровая афиша сайта","web",(1280,720),"web","Вид события, визуальная сетка сайта, текст, изображения и права"),
    Draft("VK-AVATAR","TZ-035","Аватар сообщества VK","vk",(1024,1024),"avatar","Ссылка на официальный VK, требования к аватару и безопасному обрезу"),
    Draft("VK-COVER","TZ-036","Обложка сообщества VK","vk",(1920,768),"cover","Текущие требования VK к размерам, мобильной обрезке и логотипу"),
    Draft("VK-RUBRIC-1","TZ-037","Публикация: рубрика №1","vk",(1080,1080),"rubric1","Официальное наименование и материалы первой рубрики"),
    Draft("VK-RUBRIC-2","TZ-037","Публикация: рубрика №2","vk",(1080,1080),"rubric2","Официальное наименование и материалы второй рубрики"),
    Draft("VK-RUBRIC-3","TZ-037","Публикация: рубрика №3","vk",(1080,1080),"rubric3","Официальное наименование и материалы третьей рубрики"),
    Draft("VK-RUBRIC-4","TZ-037","Публикация: рубрика №4","vk",(1080,1080),"rubric4","Официальное наименование и материалы четвёртой рубрики"),
    Draft("MERCH-NOTEPAD","TZ-059","Блокнот","merch",(1280,900),"notepad","Форма, обложка, технология печати"),
    Draft("MERCH-VEST","TZ-059","Жилетка","merch",(1280,900),"vest","Размеры жилетки, зона печати, технология и ткань"),
    Draft("MERCH-TSHIRT","TZ-060","Футболка","merch",(1280,900),"tshirt","Модель, размеры, зоны печати и ткань"),
    Draft("MERCH-STAMP","TZ-060","Штамп","merch",(1280,900),"stamp","Форма клише, производственные допуски, оттиск"),
    Draft("MERCH-STICKERS","TZ-060","Стикерпак","merch",(1280,900),"stickers","Количество стикеров, высечка, материал"),
    Draft("MERCH-CALENDAR","TZ-061","Календарь","merch",(1280,900),"calendar","Тип календаря, формат, год и механизм"),
    Draft("MERCH-POSTCARD","TZ-061","Открытка (сувенир)","merch",(1280,900),"postcard","Формат сувенира и двухсторонняя печать"),
    Draft("MERCH-THERMOMUG","TZ-061","Термокружка","merch",(1280,900),"thermomug","Форма и рабочая зона печати производителя"),
    Draft("MERCH-SHOPPER","TZ-061","Сумка-шоппер","merch",(1280,900),"shopper","Материал, размер и ограничение зоны печати"),
)

def _rect(id:str,x:float,y:float,w:float,h:float,fill="#f8fafc",stroke="#64748b",radius=0)->str:
    return f'<rect id="{id}" x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{radius}" fill="{fill}" stroke="{stroke}" stroke-width="3"/>'

def _path(id:str,d:str,fill="#f8fafc",stroke="#475569")->str:
    return f'<path id="{id}" d="{d}" fill="{fill}" stroke="{stroke}" stroke-width="5" stroke-linejoin="round"/>'

def _text(id:str,x:float,y:float,content:str,size=36,color="#1e293b",weight="normal")->str:
    return f'<text id="{id}" x="{x:.1f}" y="{y:.1f}" font-size="{size}" fill="{color}" font-weight="{weight}">{escape(content)}</text>'

def _mockup(d:Draft)->list[str]:
    # Product silhouettes are schematic geometry without any real brand art or
    # licensed photographs. Every merchandise item has its own unique outline.
    k=d.kind
    base=[
        '<g id="editable-product-outline">',
    ]
    if k=="notepad":
        base += [_rect("mockup-notepad",430,170,420,520,fill="#ffffff"),
                 _rect("mockup-spiral",418,170,25,520,fill="#e2e8f0"),
                 _rect("imprint-safe",490,295,300,210,fill="#fef3c7")]
        base += [_path(f"spiral-ring-{i}",f"M425 {215+i*55} h30",fill="none") for i in range(8)]
    elif k in ("vest","tshirt"):
        dpath=("M510 155 L615 210 L665 170 L760 155 L875 280 L785 350 L770 740 L485 740 L475 350 L380 280 Z"
               if k=="tshirt" else
               "M525 155 L595 205 L655 205 L725 155 L830 340 L760 380 L752 735 L510 735 L500 380 L430 340 Z")
        base += [_path(f"mockup-{k}",dpath),
                 _rect("imprint-safe",540,360,180,190,fill="#fef3c7",stroke="#ca8a04",radius=4)]
    elif k=="stamp":
        base += [_rect("mockup-stamp-handle",585,165,110,120,fill="#e2e8f0",radius=18),
                 _rect("mockup-stamp-base",465,290,355,255,fill="#ffffff",radius=20),
                 _rect("imprint-safe",490,325,305,160,fill="#fef3c7")]
    elif k=="stickers":
        base += [_rect("mockup-sticker-sheet",390,140,500,620,fill="#ffffff",radius=15)]
        for i,(x,y) in enumerate([(435,210),(680,210),(435,455),(680,455)]):
            base.append(_rect(f"editable-sticker-{i+1}",x,y,165,185,fill="#fef3c7",stroke="#ca8a04",radius=35))
        base.append(_rect("imprint-safe",425,198,375,475,fill="none",stroke="#ca8a04"))
    elif k=="calendar":
        base += [_rect("mockup-calendar",395,150,500,610,fill="#ffffff",radius=9),
                 _rect("mockup-binding",395,150,500,64,fill="#e2e8f0"),
                 _rect("imprint-safe",435,255,420,210,fill="#fef3c7")]
        for i in range(6):
            base.append(_path(f"editable-calendar-row-{i}",f"M455 {520+i*33} H838",fill="none"))
    elif k=="postcard":
        base += [_rect("mockup-postcard",305,225,665,420,fill="#ffffff"),
                 _rect("imprint-safe",345,265,585,340,fill="#fef3c7")]
    elif k=="thermomug":
        base += [_path("mockup-thermomug","M470 185 H770 L740 695 H500 Z"),
                 _path("mockup-cup-handle","M770 275 C990 230 990 580 755 585",fill="none"),
                 _rect("imprint-safe",535,335,175,235,fill="#fef3c7")]
    elif k=="shopper":
        base += [_path("mockup-shopper","M400 265 H880 L855 750 H425 Z",fill="#ffffff"),
                 _path("mockup-left-handle","M515 275 Q520 50 640 180",fill="none"),
                 _path("mockup-right-handle","M760 275 Q755 50 640 180",fill="none"),
                 _rect("imprint-safe",505,385,270,255,fill="#fef3c7")]
    else:
        raise ValueError("Unknown merchandise shape "+k)
    base+=['</g>',_text("product-placeholder",497,805,
                      "[ЗОНА ДЛЯ ФИРМЕННОГО ЗНАКА · СОГЛАСОВАТЬ]",24)]
    return base

def svg_for(d:Draft)->str:
    w,h=d.canvas_px
    # SVG canvas uses pixels as a PROPOSED design-space, not current official VK
    # dimensions or proof of actual merchandising production size.
    if not (700<=w<=2200 and 600<=h<=1200):
        raise ValueError("Invalid provisional draft dimensions")
    lines=[
        '<?xml version="1.0" encoding="utf-8"?>',
        f'<svg xmlns="{SVG_NS}" xmlns:mb="{TZ_NS}" width="{w}px" height="{h}px" viewBox="0 0 {w} {h}" '
        f'mb:id="{d.id}" mb:tz="{d.tz}" mb:status="{STATUS}" '
        'mb:dimensions-source="PROVISIONAL_NOT_TZ_OR_PLATFORM_APPROVED">',
        "<title>"+escape("Технический шаблон: "+d.title)+"</title>",
        '<desc>Только редактируемая техническая структура. Не фирменная айдентика, не утверждённый макет и не технические требования VK.</desc>',
        _rect("editable-background",0,0,w,h,fill="#ffffff",stroke="#ffffff"),
        '<g id="editable-wireframe" font-family="Arial,sans-serif">',
        _text("draft-watermark",35,48,TECH_NOTE,24,"#9a3412",weight="bold"),
        _text("field-type",35,101,d.title,39,weight="bold"),
    ]
    if d.category=="merch":
        lines.extend(_mockup(d))
    elif d.kind=="avatar":
        lines.extend([
            _rect("crop-uncertainty-guide",192,192,640,640,fill="none",stroke="#ca8a04",radius=320),
            _rect("logo-placeholder",350,360,324,304,fill="#fef3c7",stroke="#ca8a04",radius=60),
            _text("field-logo",390,500,"[ЛОГОТИП]",32),
            _text("field-crop-note",100,924,"[КРУГЛАЯ ОБРЕЗКА И МОБИЛЬНЫЙ ВИД УТОЧНЯЮТСЯ]",22),
        ])
    elif d.kind=="cover":
        lines.extend([
            _rect("desktop-content-guide",100,150,1720,530,fill="none",stroke="#ca8a04"),
            _rect("mobile-crop-proposal",500,150,920,530,fill="none",stroke="#ef4444"),
            _rect("logo-placeholder",200,275,320,260,fill="#fef3c7"),
            _text("field-title",590,325,"[НАЗВАНИЕ / КОНТАКТЫ]",54,weight="bold"),
            _text("field-subtitle",590,400,"[АДРЕС / АФИША / ССЫЛКА]",33),
            _text("field-mobile-warning",150,710,"[ОБРЕЗКА МОБИЛЬНОГО VK НЕ ПРОВЕРЕНА]",25),
        ])
    elif d.kind=="web":
        lines.extend([
            _rect("poster-photo-placeholder",690,160,520,445,fill="#f1f5f9"),
            _rect("poster-copy-container",45,155,580,465,fill="none"),
            _text("field-category",80,255,"[ТИП СОБЫТИЯ]",34),
            _text("field-headline",80,330,"[НАЗВАНИЕ]",55,weight="bold"),
            _text("field-date",80,420,"[ДАТА / ВРЕМЯ / МЕСТО]",30),
            _text("field-details",80,500,"[ОПИСАНИЕ / ССЫЛКА]",27),
        ])
    elif d.kind.startswith("rubric"):
        i=int(d.kind[-1])
        # Distinct typographic positions: NOT asserted to be real museum rubrics.
        orientations={1:("top",220),2:("bottom",820),3:("bottom",755),4:("split",290)}
        label,pos=orientations[i]
        if i==1:
            lines.extend([_rect("image-placeholder",90,335,900,580),_rect("category-band",90,152,900,146,fill="#f1f5f9")])
        elif i==2:
            lines.extend([_rect("image-placeholder",90,175,900,550),_rect("category-band",90,755,900,146,fill="#f1f5f9")])
        elif i==3:
            lines.extend([_rect("image-placeholder",90,170,900,480),_rect("category-band",90,680,900,210,fill="#f1f5f9")])
        else:
            lines.extend([_rect("image-placeholder",90,175,520,690),_rect("category-band",648,175,338,690,fill="#f1f5f9")])
        lines.extend([
            _text("field-category",105 if i!=4 else 670,pos,f"[РУБРИКА №{i}]",43,weight="bold"),
            _text("field-heading",105 if i!=4 else 670,pos+69,"[ЗАГОЛОВОК]",32),
            _text("field-publishing",90,1030,"[СОГЛАСОВАННЫЙ ТЕКСТ · БЕЗ РЕАЛЬНОЙ АФИШИ]",20),
        ])
    else:
        raise ValueError("Unknown category "+d.category)
    lines+=['</g>','</svg>']
    return "\n".join(lines)+"\n"

def _png_dims(raw:bytes)->tuple[int,int]:
    if not raw.startswith(b"\x89PNG\r\n\x1a\n") or raw[12:16]!=b"IHDR":
        raise ValueError("Invalid PNG signature/IHDR")
    return struct.unpack(">II",raw[16:24])

def manifest_for(directory:Path, files:bool)->dict:
    result=[]
    for d in DRAFTS:
        obj={**asdict(d),"status":STATUS,
             "dimensions_source":"PROPOSED_NOT_MUSEUM_OR_PLATFORM_CONFIRMED"}
        if files:
            png=(directory/f"TECH_{d.id}.png").read_bytes()
            obj["preview_png_sha256"]=hashlib.sha256(png).hexdigest()
        result.append(obj)
    return {"status":"ONLY_NEUTRAL_TECHNICAL_TEMPLATES_NOT_APPROVED",
            "museum_approvals":0,
            "final_merch_designs_created":0,
            "client_personal_data_included":False,
            "vk_size_platform_validated":False,
            "products_physical_dimensions_confirmed":False,
            "required_design_source":"TZ-034..037 and TZ-059..061: type/count only, not sizes",
            "items":result}

def generate(folder:Path)->dict:
    folder.mkdir(parents=True,exist_ok=True)
    for d in DRAFTS:
        source=folder/f"TECH_{d.id}.svg"
        preview=folder/f"TECH_{d.id}.png"
        source.write_text(svg_for(d),encoding="utf-8")
        subprocess.run(["rsvg-convert","--format","png","--output",str(preview),str(source)],
                       check=True,capture_output=True,timeout=15)
    m=manifest_for(folder,True)
    (folder/"DIGITAL_MERCH_MANIFEST.json").write_text(
        json.dumps(m,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return m

def verify(folder:Path)->dict:
    import sys
    if str(ROOT) not in sys.path:
        sys.path.insert(0,str(ROOT))
    from scripts.audit_design_delivery import define
    intended={item.id:item for item in DRAFTS}
    if len(intended)!=16:
        raise ValueError("Expected 16 independent digital/merch technical carriers")
    targets={t.id:t for t in define()}
    for d in DRAFTS:
        if d.id not in targets or targets[d.id].tz!=d.tz:
            raise ValueError("Draft lacks exact source TZ reference")
    mfile=folder/"DIGITAL_MERCH_MANIFEST.json"
    if not mfile.is_file():
        raise ValueError("Manifest missing")
    saved=json.loads(mfile.read_text(encoding="utf-8"))
    if saved!=json.loads(json.dumps(manifest_for(folder,True),ensure_ascii=False)):
        raise ValueError("Missing, tampered or out-of-date manifest")
    for d in DRAFTS:
        svg=folder/f"TECH_{d.id}.svg"
        if not svg.is_file() or svg.read_text(encoding="utf-8")!=svg_for(d):
            raise ValueError("Missing or modified editable SVG: "+d.id)
        root=ElementTree.fromstring(svg.read_bytes())
        nodes={node.get("id") for node in root.iter()}
        if not {"editable-background","editable-wireframe","draft-watermark","field-type"}.issubset(nodes):
            raise ValueError("Editable text or draft marking removed")
        if d.category=="merch" and not {"editable-product-outline","imprint-safe","product-placeholder"}.issubset(nodes):
            raise ValueError("Merchandise mockup lacks editable product-specific imprint area")
        if d.kind=="cover" and not {"desktop-content-guide","mobile-crop-proposal"}.issubset(nodes):
            raise ValueError("VK mobile cropping assumption not indicated")
        if root.attrib.get("{"+TZ_NS+"}status")!=STATUS:
            raise ValueError("Draft status removed")
        if _png_dims((folder/f"TECH_{d.id}.png").read_bytes())!=d.canvas_px:
            raise ValueError("Unexpected PNG dimensions: "+d.id)
    return {"editable_svgs":len(DRAFTS),"png_previews":len(DRAFTS),
            "vk":sum(d.category=="vk" for d in DRAFTS),
            "website":sum(d.category=="web" for d in DRAFTS),
            "merch":sum(d.category=="merch" for d in DRAFTS),
            "approved":0,"all_dimensions_provisional":True}

def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--output",type=Path,default=OUTPUT)
    ap.add_argument("--verify",action="store_true")
    args=ap.parse_args()
    if not args.verify:
        generate(args.output)
    print("DIGITAL/MERCH TECHNICAL QA:",json.dumps(verify(args.output),ensure_ascii=False))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
