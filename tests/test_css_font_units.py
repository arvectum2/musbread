import unittest
from scripts.check_css_font_units import disallowed

class FontSizeContractTests(unittest.TestCase):
    def test_accepts_relative_units(self):
        self.assertFalse(disallowed("h1 { font-size: clamp(2rem, 3em, 4rem); }"))

    def test_rejects_viewport_units_for_font_size(self):
        self.assertEqual(disallowed("h1 { font-size: clamp(2rem, 4vw, 4rem); }"),
                         ["clamp(2rem, 4vw, 4rem)"])

    def test_rejects_px_pt_and_percent_for_text(self):
        self.assertEqual(len(disallowed("p{font-size:16px}h1{font-size:12pt}h2{font-size:95%}")), 3)

    def test_other_dimension_pixels_are_allowed(self):
        self.assertFalse(disallowed("div { width: 80vw; padding: 4px; font-size: 1rem; }"))

if __name__ == "__main__":
    unittest.main()
