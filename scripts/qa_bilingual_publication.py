#!/usr/bin/env python3
"""QA the existing CMS-English -> static-route contract on disposable demo data.
Always restore the golden published.json and rebuild the original public site.
The script never publishes a real translation or touches a customer service.
"""
from pathlib import Path
import hashlib,json,subprocess,re

ROOT=Path(__file__).resolve().parents[1]
WEB=ROOT/"apps/web"
SOURCE=WEB/"src/data/published.json"
DATA=SOURCE.read_bytes()
BEFORE=hashlib.sha256(DATA).hexdigest()
def run_build():
 subprocess.run(["npm","run","build"],cwd=WEB,check=True,
                stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,text=True)
try:
 obj=json.loads(DATA)
 obj['sections']=[{'slug':'museum','title':'Музей','parent_slug':None,'sort_order':0,'legacy_path':None}]
 original=obj["entries"][0]
 assert original["type"]=="excursion"
 obj["entries"].append({
   "type":"news","slug":"qa-bilingual-announcement","title":"Проверочная новость",
   "excerpt":"Только тест QA","body":"Только тест","sort_order":100,
   "translations":{"en":{
      "title":"Bilingual publication QA","h1":"English-only test heading",
      "excerpt":"Temporary translated preview",
      "body":"<p>Sanitized English content from approved CMS translation.</p>",
      "seo_title":"Museum bilingual QA title",
      "seo_description":"QA translation export, not a real museum page."
   }}
 })
 obj["entries"].append({
   "type":"news","slug":"qa-untranslated-announcement","title":"Новость без перевода",
   "excerpt":"Только QA","body":"Исходная публикация без утверждённого EN перевода",
   "sort_order":101
 })
 obj["entries"].append({
   "type":"page","slug":"qa-new-nested-page","title":"Новая вложенная страница",
   "excerpt":"Только QA","body":"Добавление страницы в существующий раздел",
   "section_slug":"museum","sort_order":102
 })
 SOURCE.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 run_build()
 out=WEB/"out"
 ru=(out/"news/qa-bilingual-announcement/index.html").read_text()
 en=(out/"en/news/qa-bilingual-announcement/index.html").read_text()
 nested=(out/"museum/qa-new-nested-page/index.html").read_text()
 listing=(out/"guide/museum/index.html").read_text()
 assert "Read in English" in ru
 assert 'href="/en/news/qa-bilingual-announcement/"' in ru
 assert 'lang="en"' in en and "English-only test heading" in en
 assert "Museum bilingual QA title" in en and "Sanitized English content" in en
 assert 'href="/news/qa-bilingual-announcement/"' in en
 assert "/en/news/qa-bilingual-announcement/" in en
 assert "qa-untranslated-announcement" not in str(list((out/"en/news").glob("*")))
 assert "Новая вложенная страница" in nested
 assert "Новая вложенная страница" in listing
 assert 'href="/museum/qa-new-nested-page/"' in listing
 print("BILINGUAL_AND_SECTION_QA_PASS: valid EN translation, RU↔EN links and SEO, unpublished EN absent, new CMS-assigned page listed")
finally:
 SOURCE.write_bytes(DATA)
 assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==BEFORE
 run_build()
 assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==BEFORE
 assert not (WEB/"out/en/news/qa-bilingual-announcement/index.html").exists()
 assert not (WEB/"out/museum/qa-new-nested-page/index.html").exists()
 print("GOLDEN_PUBLIC_SITE_RESTORED",BEFORE)
