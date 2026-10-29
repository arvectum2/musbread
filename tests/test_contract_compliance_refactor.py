"""Regression protection for contract-driven production boundary fixes."""
from __future__ import annotations
import unittest
from pathlib import Path
from scripts.check_css_font_units import disallowed

ROOT=Path(__file__).resolve().parents[1]

class ContractDrivenRefactorTests(unittest.TestCase):
    def test_font_sizes_are_only_relative_rem_or_em(self):
        css=(ROOT/"apps/web/src/app/globals.scss").read_text(encoding="utf-8")
        self.assertEqual(disallowed(css), [])
        self.assertIn("@media(max-width:650px)",css)
        self.assertIn(".inner-page h1{font-size:2.25rem}",css)

    def test_export_default_is_absolute_without_parent_components(self):
        code=(ROOT/"apps/cms/app/Console/Commands/ExportMuseumSnapshot.php").read_text()
        self.assertIn("$webRoot = dirname(base_path()).'/web';",code)
        for part in ("src/data/published.json","public/snapshot-manifest.json",
                     "public/media","public/documents"):
            self.assertIn("$webRoot.'/"+part+"'",code)
        self.assertNotIn("base_path('../web/",code)

    def test_safe_stage_rejects_dot_and_link_bypass(self):
        php=(ROOT/"apps/cms/app/Support/MuseumSnapshotStagedCommit.php").read_text()
        self.assertIn("in_array('..', $parts, true)",php)
        self.assertIn("is_link($current)",php)
        self.assertIn("Unsafe export destination",php)

    def test_private_nginx_serves_current_jodit_not_retired_tinymce(self):
        config=(ROOT/"infra/nginx/private-cms.conf").read_text()
        ci=(ROOT/".github/workflows/web-ci.yml").read_text()
        self.assertIn("moonshine|museum-jodit",config)
        self.assertNotIn("moonshine|moonshine-tinymce",config)
        self.assertIn("museum-jodit/editor.js)",ci)
        self.assertIn("moonshine-tinymce/tinymce.min.js)",ci)
        self.assertIn("REMOVED_FROM_RUNTIME_AND_PUBLISHED_ASSETS",ci)

    def test_nginx_ci_shell_lines_do_not_contain_literal_escaped_newlines(self):
        ci=(ROOT/".github/workflows/web-ci.yml").read_text()
        self.assertNotIn(r"\n          sudo", ci)
        self.assertNotIn(r"\n          printf", ci)
        self.assertNotIn(r"\n          test", ci)

    def test_ci_checks_both_normative_sources(self):
        ci=(ROOT/".github/workflows/web-ci.yml").read_text()
        self.assertIn("scripts/check_speckit_tz.py --check",ci)
        self.assertIn("scripts/audit_signed_contract.py --check",ci)
        self.assertIn("tests/test_signed_contract_spec.py",ci)


if __name__=="__main__":
    unittest.main()
