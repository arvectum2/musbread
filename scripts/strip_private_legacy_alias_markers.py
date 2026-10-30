#!/usr/bin/env python3
"""Fail-closed removal of transient alias markers before ANY static web export.

Markers are builder control files, never public assets. The source-verified
fallback HTML remains at its historical URL; source CSV verifies each mapping.
"""
from __future__ import annotations
import argparse
import csv
from pathlib import Path
try:
    from .build_museum_legacy_page_aliases import render_alias
except ImportError:  # called as a script from apps/web
    from build_museum_legacy_page_aliases import render_alias

ROOT=Path(__file__).resolve().parents[1]
DEFAULT_CSV=ROOT/'docs/source-migration/LEGACY_MUSEUM_PAGE_ALIASES_20261018.csv'


def strip(root: Path, csv_file: Path=DEFAULT_CSV) -> int:
    if not root.is_dir() or root.is_symlink() or not (root/'index.html').is_file():
        raise ValueError('Refusing to clean missing/symlink public build')
    with csv_file.open(encoding='utf-8-sig',newline='') as handle:
        rows=list(csv.DictReader(handle,delimiter=';'))
    aliases={}
    for row in rows:
        if row['mode'].startswith('static-meta-refresh'):
            source=row['legacy_path']; target=row['new_relative_url']
            if not source.startswith('/') or not target.startswith('/') or '..' in (source+target):
                raise ValueError('Unsafe recorded legacy mapping')
            alias=root/source.lstrip('/')/'index.html'
            if alias in aliases:
                raise ValueError('Duplicate alias record '+source)
            aliases[alias]=(source,target)
    expected_markers={p.parent/'.musbread-legacy-alias' for p in aliases}
    existing=set(root.rglob('.musbread-legacy-alias'))
    if existing!=expected_markers:
        raise ValueError(f'Unexpected or missing legacy marker(s): extra={len(existing-expected_markers)} missing={len(expected_markers-existing)}')
    if not aliases:
        raise ValueError('No signed original aliases to verify')
    # Phase 1 validates the *entire* export before any unlink: no partial clean.
    for alias,(source,target) in aliases.items():
        marker=alias.parent/'.musbread-legacy-alias'
        if marker.is_symlink() or not marker.is_file() or alias.is_symlink() or not alias.is_file():
            raise ValueError('Unsafe legacy marker or HTML file '+source)
        if marker.read_text(encoding='utf-8')!=target+'\n' or alias.read_text(encoding='utf-8')!=render_alias(source,target):
            raise ValueError('Legacy fallback bytes or route manifest changed '+source)
    # Phase 2 drops ephemeral control markers only, retaining signed fallback HTML.
    for marker in sorted(expected_markers):
        marker.unlink()
    return len(expected_markers)


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('export',type=Path)
    args=ap.parse_args()
    print('STRIPPED_LEGACY_ALIAS_MARKERS',strip(args.export))
