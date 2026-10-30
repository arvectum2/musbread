#!/usr/bin/env python3
"""Explicit, fail-closed test profiles for public GitHub vs private museum archive.

GitHub checkout intentionally has NO .local_archive and NO complete 101-document
museum export. Archive-dependent tests remain mandatory on the Mac mini release
workstation; a passing public CI is not a production release certificate.
All newly added tests run in public CI unless explicitly reviewed and classified.
"""
from __future__ import annotations
import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE_TESTS = frozenset('test_audit_museum_alt_provenance\ntest_complete_museum_static_release\ntest_museum_deep_source_documents\ntest_museum_deep_source_images\ntest_museum_government_and_historical_exhibition_sources\ntest_museum_legacy_page_aliases\ntest_museum_new_source_first_sections_and_crosslinks\ntest_museum_news_index_payload\ntest_museum_official_robots_sitemap_baseline\ntest_museum_original_documents_static\ntest_museum_original_long_titles_seo\ntest_museum_pdf_openability_http_report\ntest_museum_self_hosted_static_photos\ntest_museum_seo_cutover_readiness\ntest_museum_source_news_pagination_legacy\ntest_museum_source_only_indexing_gate\ntest_museum_visually_reviewed_alts\ntest_official_museum_news_archive\ntest_official_node_linked_exhibitions\ntest_primary_contract_questions_audit'.splitlines())


def test_files(profile: str) -> list[Path]:
    files = sorted((ROOT / "tests").glob("test_*.py"))
    names = {path.stem for path in files}
    missing = ARCHIVE_TESTS - names
    if missing:
        raise RuntimeError(f"Archived test inventory missing from repository: {sorted(missing)}")
    if profile == "public":
        return [p for p in files if p.stem not in ARCHIVE_TESTS]
    if profile == "archive":
        return [p for p in files if p.stem in ARCHIVE_TESTS]
    return files


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=("public", "archive", "all"), required=True)
    args = parser.parse_args()
    selected = test_files(args.profile)
    print(f"TEST_PROFILE={args.profile} selected_files={len(selected)} ",
          f"archive_only_files={len(ARCHIVE_TESTS)} total_files={len(test_files('all'))}", flush=True)
    if args.profile == "public":
        print("Private source provenance: NOT TESTED by GitHub; full --profile all is mandatory on Mac mini before release.", flush=True)
    if not selected:
        raise RuntimeError("Empty test profile is not acceptable")
    return subprocess.run([sys.executable, "-m", "unittest", *[str(p) for p in selected], "-v"], cwd=ROOT).returncode


if __name__ == "__main__":
    sys.exit(main())
