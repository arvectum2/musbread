"""Pure guards for native Safari AX measurement; never opens GUI in unit tests."""
import unittest
from scripts.qa_native_safari_ax_zoom import assert_native_safari_measurement,WIDTHS,ROUTES,ZOOM_STEPS

class SafariNativeAccessibilityGuards(unittest.TestCase):
    def setUp(self):
        self.sample={
            "skipLabelHeight":30,"webWidth":768,"scrollWidth":768,
            "horizontalScrollbars":0,"hasHeadings":True
        }
    def test_genuine_200pct_safari_web_area_passes(self):
        self.assertTrue(assert_native_safari_measurement(self.sample,768,5))
    def test_no_heading_or_skip_link_fails(self):
        self.sample["skipLabelHeight"]=0
        self.assertFalse(assert_native_safari_measurement(self.sample,768,5))
        self.sample["skipLabelHeight"]=30
        self.sample["hasHeadings"]=False
        self.assertFalse(assert_native_safari_measurement(self.sample,768,5))
    def test_unexpected_zoom_level_fails(self):
        self.sample["skipLabelHeight"]=15
        self.assertFalse(assert_native_safari_measurement(self.sample,768,5))
    def test_horizontal_scrollbar_fails(self):
        self.sample["horizontalScrollbars"]=1
        self.assertFalse(assert_native_safari_measurement(self.sample,768,5))
    def test_mismatched_web_area_width_fails(self):
        self.sample["webWidth"]=970
        self.assertFalse(assert_native_safari_measurement(self.sample,768,5))
    def test_expected_coverage(self):
        self.assertEqual(len(WIDTHS)*len(ROUTES)*len(ZOOM_STEPS),108)
        self.assertEqual(ZOOM_STEPS,(0,1,2,3,4,5))

if __name__=="__main__":
    unittest.main()
