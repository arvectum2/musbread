#!/usr/bin/env python3
"""Pin museum-owned Yandex Maps constructor ID from original contact page.

No geocoding inference or access to visitor data. The official site already
uses the Yandex constructor. New site only instantiates an iframe after click.
"""
import hashlib,json,re
from pathlib import Path
from datetime import datetime,timezone
from urllib.parse import urlsplit,parse_qs
from urllib.request import Request,urlopen
from lxml import html
ROOT=Path(__file__).resolve().parents[1]
ORIGIN="https://muzei-xleb.ru/kontakty"
MAP_PATTERN=re.compile(r'^[A-Za-z0-9_-]{20,70}$')
EXPECTED="He-zSYLQhEw4RVkaykZ0Rpr1lOWx3f9O"
def fetch(url):
    with urlopen(Request(url,headers={"User-Agent":"Mozilla/5.0 (MusBread official museum map source provenance)","Accept":"text/html"}),timeout=28) as r:
        if r.status!=200 or "text/html" not in r.headers.get("Content-Type",""):
            raise RuntimeError("Not HTTP200 HTML "+url)
        return r.read(1600000).decode("utf-8","replace")
def main():
    root=html.fromstring(fetch(ORIGIN))
    scripts=[e.get("src") for e in root.xpath('//script[@src]') if
             "api-maps.yandex.ru/services/constructor/1.0/js/" in (e.get("src") or "")]
    if len(scripts)!=1:raise RuntimeError("Expected one embedded official Yandex constructor in contact page")
    original=scripts[0];split=urlsplit(original)
    if split.scheme!="https" or split.hostname!="api-maps.yandex.ru" or split.path!="/services/constructor/1.0/js/":
        raise RuntimeError("Unexpected original map source")
    params=parse_qs(split.query)
    sid=params.get("sid",[""])[0]
    if sid!=EXPECTED or not MAP_PATTERN.fullmatch(sid):
        raise RuntimeError("Official museum map constructor identity changed; human verify")
    if params.get("sourceType")!=["constructor"] or params.get("lang")!=["ru_RU"]:
        raise RuntimeError("Original map switched provider/type")
    widget="https://yandex.ru/map-widget/v1/?um=constructor%3A"+sid+"&source=constructor"
    widget_html=fetch(widget)
    if "<html" not in widget_html.lower():raise RuntimeError("Museum constructor map widget did not return HTML")
    saved={
      "museum_contact_source":ORIGIN,
      "map_provider":"Яндекс Карты",
      "constructor_id":sid,
      "official_original_script_url":original,
      "embedded_after_user_action_only":True,
      "no_inferred_coordinates":True,
      "widget_iframe_url":widget,
      "http_200_verified_utc":datetime.now(timezone.utc).isoformat(timespec="seconds"),
      "original_script_url_sha256":hashlib.sha256(original.encode()).hexdigest(),
      "privacy_note":"Yandex request only after pressing Show map; direct address search as no-embed fallback",
    }
    out=ROOT/"apps/web/src/data/official-museum-map.json"
    temp=out.with_suffix(".json.tmp")
    temp.write_text(json.dumps(saved,ensure_ascii=False,indent=2)+"\n")
    temp.replace(out)
    print("VERIFIED official museum Yandex constructor",sid, "widget HTTP 200, no new coordinates")
if __name__=="__main__":main()
