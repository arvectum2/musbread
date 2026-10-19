"""Pure guards for REAL Firefox zoom evidence, no browser side effects."""
import unittest
from scripts.qa_native_firefox_zoom import verify_real_native_zoom,PHYSICAL_WIDTHS,ROUTES,LEVELS

class NativeFirefoxZoomGuards(unittest.TestCase):
    def setUp(self):
        self.sample={"url":"/news/","h1":True,"ratio":2.0,
                     "scriptZoom":"","scrollWidth":384,"cssWidth":384}
    def test_true_browser_zoom_verified_without_overflow(self):
        self.assertEqual(verify_real_native_zoom(self.sample,"/news/",200),(True,False))
    def test_css_zoom_not_confused_with_browser_zoom(self):
        self.sample["scriptZoom"]="2"
        self.assertEqual(verify_real_native_zoom(self.sample,"/news/",200),(False,False))
    def test_wrong_actual_ratio_rejected(self):
        self.sample["ratio"]=1.0
        self.assertEqual(verify_real_native_zoom(self.sample,"/news/",200),(False,False))
    def test_real_horizontal_overflow_rejected(self):
        self.sample["scrollWidth"]=430
        self.assertEqual(verify_real_native_zoom(self.sample,"/news/",200),(True,True))
    def test_missing_headline_or_wrong_route_rejected(self):
        self.sample["h1"]=False
        self.assertFalse(verify_real_native_zoom(self.sample,"/news/",200)[0])
        self.sample["h1"]=True
        self.assertFalse(verify_real_native_zoom(self.sample,"/search/",200)[0])
    def test_measured_native_coverage_is_90_cases(self):
        self.assertEqual(len(PHYSICAL_WIDTHS)*len(ROUTES)*len(LEVELS),90)
        self.assertEqual([n for n,_ in LEVELS],[100,120,150,170,200])

if __name__=="__main__":
    unittest.main()
