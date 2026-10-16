#!/usr/bin/env python3
"""Temporarily build a 4-level CMS snapshot, then ALWAYS restore golden JSON."""
from pathlib import Path
import hashlib,json,subprocess,sys
root=Path(__file__).resolve().parents[1]
web=root/'apps/web'
snapshot=web/'src/data/published.json'
original=snapshot.read_bytes()
new=json.loads(original)
new['sections']=[
 {'slug':'museum','title':'Музей','parent_slug':None,'sort_order':0,'legacy_path':None},
 {'slug':'visitors','title':'Посетителям','parent_slug':None,'sort_order':1,'legacy_path':None},
 {'slug':'museum-history','title':'История музея','parent_slug':'museum','sort_order':0,'legacy_path':None},
 {'slug':'new-gallery','title':'Новая галерея','parent_slug':'museum-history','sort_order':0,'legacy_path':None},
 {'slug':'fresh-service','title':'Услуга без изменения React','parent_slug':'new-gallery','sort_order':0,'legacy_path':None},
]
try:
 snapshot.write_text(json.dumps(new,ensure_ascii=False,indent=2)+'\n')
 subprocess.run(['npm','run','build'],cwd=web,check=True,stdout=subprocess.DEVNULL)
 for slug,expected in [
  ('museum','Новая галерея'),('museum-history','Новая галерея'),
  ('new-gallery','Услуга без изменения React'),('fresh-service','Новая галерея'),
 ]:
  html=(web/'out/guide'/slug/'index.html').read_text()
  assert expected in html,(slug,expected)
  assert 'Перейти' in html or 'Подразделы' in html,slug
 print('NESTED_STATIC_HTML_OK',len(new['sections']),'sections, 4-level path, generated routes',flush=True)
finally:
 snapshot.write_bytes(original)
 assert snapshot.read_bytes()==original
 # Never leave the generated public site carrying synthetic QA content.
 subprocess.run(['npm','run','build'],cwd=web,check=True,stdout=subprocess.DEVNULL)
 print('GOLDEN_SNAPSHOT_RESTORED',hashlib.sha256(original).hexdigest(),flush=True)
