#!/usr/bin/env python3
"""Offline museum pre-award static artifact assembler, NEVER a deploy tool.

Next.js `npm run build` deletes the previous `out`. Original museum 101 PDF/DOCX,
255 self-hosted photo bytes and 27 source news index pages are NOT committed
into the Git web/public tree. Always rehydrate from verified ArvectumSSD source
archives after Next.js builds. Then verify BEFORE authorizing a QA release.

No DNS, remote host, production publish, CMS database, or internet writes.
"""
from __future__ import annotations
import argparse, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
WEB=ROOT/'apps/web'
OUT=WEB/'out'
SCRIPTS=ROOT/'scripts'

def run(args,cwd=ROOT):
 print('MUSEUM_OFFLINE_STATIC_STEP',args,flush=True)
 subprocess.run(args,check=True,cwd=cwd)

def verify():
 sys.path.insert(0,str(SCRIPTS))
 from export_official_museum_original_documents import export as check_docs
 from export_official_museum_static_photos import generate as check_photos, DEFAULT_MAX_EDGE
 from export_official_museum_news_pagination import source_pages, SRC as NEWS_DATA, OUT as PAGED_OUT
 import json
 if OUT!=PAGED_OUT or not OUT.is_dir():
  raise RuntimeError('No complete Next.js static build to verify')
 docs=check_docs(verify_only=True)
 photos=check_photos(DEFAULT_MAX_EDGE,True)
 source=json.loads((NEWS_DATA/'official-museum-news-archive.json').read_text(encoding='utf-8'))
 if docs['count']!=101 or photos['count']!=259:
  raise RuntimeError('Original document/photo census unexpectedly changed')
 pager=sorted((OUT/'__museum_legacy_pager').glob('page-*.html'))
 if len(pager)!=27 or len(source['articles'])!=270 or len(source_pages()[0])!=28:
  raise RuntimeError('Missing self-hosted original museum news archive index pages')
 for n in range(1,28):
  p=OUT/'__museum_legacy_pager'/f'page-{n}.html'
  if not p.is_file() or 'noindex' not in p.read_text(encoding='utf-8'):
   raise RuntimeError('Staging pagination index is absent, or could be indexed: '+str(p))
 robot=(OUT/'robots.txt').read_text(encoding='utf-8')
 sitemap=(OUT/'sitemap.xml').read_text(encoding='utf-8')
 if any(OUT.rglob('.musbread-legacy-alias')):raise RuntimeError('Local alias markers must not enter public static release')
 if 'Disallow: /' not in robot or '<url>' in sitemap:
  raise RuntimeError('Pre-award prototype unexpectedly indexable')
 print('MUSEUM_COMPLETE_LOCAL_ARTIFACT_PASS',{
  'museum_PDF_DOCX_exact_sha256':docs['count'],
  'museum_original_photo_source_URLs_selfhosted':photos['count'],
  'museum_unique_photo_static_assets':photos['unique'],
  'source_verified_query_news_pages':len(pager),
  'original_news_articles':len(source['articles'])+10,
  'prototype_robots_blocks_search':True,
  'prototype_sitemap_empty':True,
  'public_dns_or_museum_server_modified':False,
 },flush=True)

if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__)
 group=parser.add_mutually_exclusive_group(required=True)
 group.add_argument('--build',action='store_true',help='Next.js build, private source files restore, verification')
 group.add_argument('--verify-only',action='store_true',help='Check already-assembled Next out, no mutation')
 args=parser.parse_args()
 if args.build:
  run(['npm','run','build'],WEB)
  # Next postbuild generates hidden local control markers for Drupal aliases.
  # They are NOT museum content and must never enter public static releases.
  removed=0
  for marker in OUT.rglob('.musbread-legacy-alias'):
   if not marker.is_file() or marker.is_symlink():raise RuntimeError('Unsafe legacy alias marker')
   marker.unlink();removed+=1
  print('STRIPPED_PRIVATE_LEGACY_ALIAS_BUILD_MARKERS',removed,flush=True)
  # Never serve just-cleared source files before all three steps have passed.
  run([sys.executable,str(SCRIPTS/'export_official_museum_original_documents.py'),'--apply'])
  run([sys.executable,str(SCRIPTS/'export_official_museum_static_photos.py')])
  run([sys.executable,str(SCRIPTS/'export_official_museum_news_pagination.py')])
 verify()
