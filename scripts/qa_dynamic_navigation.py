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
# TZ-197: published content is discoverable inside its assigned leaf section;
# unrelated content must not leak and the canonical page must point back.
new['entries']=[{**entry, 'section_slug': 'fresh-service' if entry['slug']=='museum-about' else None}
                for entry in new['entries']]
new['entries'] += [{**new['entries'][0], 'slug': 'new-deep-page', 'type':'page',
                    'title': 'Новое содержимое в существующем разделе',
                    'excerpt': 'Публикация появится без изменений компонента навигации',
                    'section_slug': 'fresh-service'}]
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
 leaf=(web/'out/guide/fresh-service/index.html').read_text()
 assert 'Новое содержимое в существующем разделе' in leaf
 assert 'href="/museum/new-deep-page/"' in leaf
 assert 'href="/museum/museum-about/"' in leaf
 assert 'demo-news' not in leaf, 'unrelated entries must not appear in leaf section'
 detail=(web/'out/museum/new-deep-page/index.html').read_text()
 assert 'href="/guide/fresh-service/"' in detail
 print('NESTED_STATIC_HTML_OK',len(new['sections']),'sections, 4-level path, generated routes + assigned entries',flush=True)
finally:
 snapshot.write_bytes(original)
 assert snapshot.read_bytes()==original
 # Never leave the generated public site carrying synthetic QA content.
 subprocess.run(['npm','run','build'],cwd=web,check=True,stdout=subprocess.DEVNULL)
 print('GOLDEN_SNAPSHOT_RESTORED',hashlib.sha256(original).hexdigest(),flush=True)
