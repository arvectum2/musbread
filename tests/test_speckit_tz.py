"""Offline verification of the 325-item Spec Kit source traceability ledger."""
import copy
import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/check_speckit_tz.py"
spec = importlib.util.spec_from_file_location("musbread_speckit_tz", SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class SpecKitTzTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = mod.registry()
        cls.source_map = json.loads(mod.MAP.read_text(encoding="utf-8"))

    def test_complete_325_ids_and_offline_integrity(self):
        mod.validate_map(self.source_map, self.rows, None)
        self.assertEqual(len(self.source_map["items"]), 325)
        self.assertEqual(self.source_map["source_physical_lf_lines"], 485)
        self.assertEqual(mod.SHA, self.source_map["source_sha256"])
        self.assertEqual(mod.sha(mod.MAP.read_bytes()), mod.PINNED_MAP_SHA)

    def test_projection_is_exactly_generated(self):
        self.assertEqual(mod.SPEC.read_text(encoding="utf-8"),
                         mod.render_spec(self.source_map, self.rows))
        self.assertIn("325 obligations", mod.render_spec(self.source_map, self.rows))

    def test_explicit_physical_lf_not_python_unicode_splitlines(self):
        raw = "first\u2028second\nthird\n".encode("utf-8")
        self.assertEqual(len(mod.physical_lines(raw)), 2)
        self.assertEqual(len(raw.decode().splitlines()), 3)
        self.assertEqual(mod.physical_lines(raw)[0], "first\u2028second".encode())

    def test_composite_clause_scope_parser(self):
        self.assertEqual(mod.expected_sections("1.1–1.3"), ["1.1", "1.2", "1.3"])
        self.assertEqual(mod.expected_sections("1.6, 2.1.1, 2.2.3.1"),
                         ["1.6", "2.1.1", "2.2.3.1"])
        self.assertEqual(mod.expected_sections("Раздел 4 / 2.2.2.6"),
                         ["4", "2.2.2.6"])
        self.assertEqual(mod.expected_sections("Приложение 1"), ["appendix1"])

    def test_references_reject_bad_and_out_of_bounds(self):
        self.assertEqual(mod.references("139,150-152,264"), [139, 150, 151, 152, 264])
        for bad in ["", "1,1", "0", "486", "2-1", "12 to 19", "12;13"]:
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                mod.references(bad)

    def test_reject_missing_reordered_or_overwritten_atom(self):
        for mutate in [
            lambda m: m["items"].pop(),
            lambda m: m["items"][0].update(id="TZ-999"),
            lambda m: m["items"][0].update(clause="2.2.3.4"),
            lambda m: m["items"][0].update(atomic_registry_summary="AI summary not sourced"),
            lambda m: m["items"][0].update(physical_lines=[45]),
            lambda m: m["items"][0].update(source_line_sha256=["not-a-hash"]),
            lambda m: m["items"][0].update(quote_line=485),
            lambda m: m["items"][0].update(exact_excerpt=""),
            lambda m: m["items"][0].update(excerpt_is_full_clause=True),
            lambda m: m.update(source_sha256="0"*64),
        ]:
            with self.subTest(mutate=repr(mutate)):
                changed = copy.deepcopy(self.source_map)
                mutate(changed)
                with self.assertRaises((ValueError, KeyError)):
                    mod.validate_map(changed, self.rows, None)

    def test_spec_does_not_override_source_or_customer_acceptance(self):
        self.assertFalse(self.source_map["original_in_public_git"])
        text = mod.SPEC.read_text(encoding="utf-8")
        self.assertIn("signed annex outranks this extract", text)
        self.assertIn("NOT full clause", text)
        self.assertIn("NOT a quote", text)
        self.assertIn("original NOT verified", (ROOT / "scripts/check_speckit_tz.py").read_text(encoding="utf-8"))

    def test_original_source_line_fingerprint_is_immutable(self):
        entry = self.source_map["items"][99]
        self.assertEqual(entry["id"], "TZ-100")
        self.assertEqual(entry["physical_lines"], [151])
        self.assertEqual(entry["quote_line"], 151)
        self.assertTrue(entry["source_line_sha256"][0])
        self.assertIn("доверенных IP", entry["exact_excerpt"])


if __name__ == "__main__":
    unittest.main()
