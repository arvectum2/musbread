"""CP-31D technical museum/office carriers: genuine vector and PDF checks."""
import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from xml.etree import ElementTree as ET

from pypdf import PdfReader

from scripts.generate_secondary_carriers import (
    ROOT, OUTPUT, CARRIERS, MB, SVG, STATUS, EXPECTED, geometry, make_svg, generate, verify
)

class SecondaryCarrierTests(unittest.TestCase):
    def test_every_original_tz_043_053_has_separate_carrier(self):
        ids={x.id for x in CARRIERS}
        self.assertEqual(len(CARRIERS),13)
        self.assertEqual(ids,EXPECTED)
        self.assertEqual(sum(x.id.startswith("SIGN-") for x in CARRIERS),2)
        self.assertEqual(sum(x.id.startswith("CARD-") for x in CARRIERS),2)
        self.assertEqual(sum(x.id.startswith("BADGE-") for x in CARRIERS),2)
        with (ROOT/"docs/tz-audit/requirements.psv").open() as file:
            tz=file.read()
        for x in CARRIERS:
            self.assertIn(x.tz,tz)
            self.assertEqual(geometry(x)["status"],STATUS)
            self.assertNotEqual(x.dimensions_source,"TZ_EXACT")

    def test_sizes_are_proposed_not_tz_exact_and_pixels_are_minimum(self):
        for x in CARRIERS:
            item=geometry(x)
            w,h=x.trim_mm
            b=x.bleed_mm
            self.assertEqual(item["full_artboard_mm"],[w+2*b,h+2*b])
            self.assertGreaterEqual(item["minimum_raster_pixels_for_future_print_300dpi"][0],
                                    (w+2*b)*300/25.4)
            self.assertGreaterEqual(item["minimum_raster_pixels_for_future_print_300dpi"][1],
                                    (h+2*b)*300/25.4)
            self.assertLess(x.safe_mm,min(w,h)/2)
        with self.assertRaisesRegex(ValueError,"Unsupported"):
            geometry(replace(CARRIERS[0],safe_mm=95))

    def test_editable_geometry_markings_and_no_real_personal_data(self):
        all_text=""
        for c in CARRIERS:
            xml=make_svg(c)
            root=ET.fromstring(xml)
            self.assertEqual(root.attrib[MB+"status"],STATUS)
            ids={el.attrib.get("id") for el in root.iter()}
            self.assertTrue({"guides-trim","guides-safe","trim-guide","safe-guide",
                             "editable-content","draft-watermark","crop-marks"}.issubset(ids))
            self.assertGreaterEqual(len([el for el in root.iter() if el.tag==SVG+"text"]),3)
            self.assertNotIn("<script",xml)
            self.assertNotIn("<image",xml)
            self.assertNotIn("javascript:",xml)
            all_text+=xml
            if c.id.startswith(("CARD-","BADGE-")):
                self.assertIn("field-person",ids)
                self.assertIn("field-role",ids)
                self.assertIn("[",xml)
            if c.id.startswith("SIGN-"):
                self.assertIn("editable-direction-arrow",ids)
        self.assertNotIn("Иванов Иван",all_text)

    def test_all_pdf_previews_have_actual_mm_mediabox(self):
        result=verify(OUTPUT)
        self.assertEqual(result["svg"],13)
        self.assertEqual(result["pdf_previews"],13)
        self.assertFalse(result["dimensions_approved"])
        self.assertEqual(result["approved"],0)
        manifest=json.loads((OUTPUT/"SECONDARY_MANIFEST.json").read_text())
        self.assertEqual(len(manifest["carriers"]),13)
        self.assertFalse(manifest["museum_personal_data_used"])
        for c in CARRIERS:
            media=PdfReader(str(OUTPUT/f"TECH_{c.id}.pdf")).pages[0].mediabox
            aw,ah=geometry(c)["full_artboard_mm"]
            self.assertAlmostEqual(float(media.width)*25.4/72,aw,delta=.15)
            self.assertAlmostEqual(float(media.height)*25.4/72,ah,delta=.15)

    def test_changed_svg_and_pdf_geometry_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            where=Path(folder)
            generate(where,render_pdf=True)
            self.assertEqual(verify(where)["svg"],13)
            svg=where/"TECH_LABEL.svg"
            svg.write_text(svg.read_text().replace("НЕ УТВЕРЖДЕНО","УТВЕРЖДЕНО"))
            with self.assertRaisesRegex(ValueError,"changed"):
                verify(where)
            generate(where,render_pdf=True)
            pdf=where/"TECH_BADGE-1.pdf"
            pdf.write_bytes((where/"TECH_OFFICE-BLANK.pdf").read_bytes())
            with self.assertRaisesRegex(ValueError,"geometry mismatch"):
                verify(where)

    def test_unapproved_metadata_cannot_be_removed_silently(self):
        with tempfile.TemporaryDirectory() as folder:
            where=Path(folder)
            generate(where,render_pdf=True)
            f=where/"SECONDARY_MANIFEST.json"
            content=f.read_text()
            f.write_text(content.replace("ONLY_PREAWARD_TECHNICAL_DRAFTS_NOT_MUSEUM_APPROVED",
                                         "MUSEUM_APPROVED"))
            with self.assertRaisesRegex(ValueError,"manifest"):
                verify(where)

if __name__=="__main__":
    unittest.main()
