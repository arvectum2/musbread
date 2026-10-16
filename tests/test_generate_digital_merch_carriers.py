"""CP-32D: source-traceable SVG/PNG wireframes; never official brand deliverables."""
import json
import struct
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from xml.etree import ElementTree as ET

from scripts.audit_design_delivery import define
from scripts.generate_digital_merch_carriers import (
    OUTPUT, ROOT, DRAFTS, STATUS, TZ_NS, SVG_NS, TECH_NOTE,
    _png_dims, svg_for, generate, verify
)


class DigitalMerchCarrierTests(unittest.TestCase):
    def test_all_six_vk_and_nine_merch_and_one_website_have_original_tz(self):
        expected={
            "WEB-POSTER","VK-AVATAR","VK-COVER","VK-RUBRIC-1","VK-RUBRIC-2",
            "VK-RUBRIC-3","VK-RUBRIC-4",
            "MERCH-NOTEPAD","MERCH-VEST","MERCH-TSHIRT","MERCH-STAMP",
            "MERCH-STICKERS","MERCH-CALENDAR","MERCH-POSTCARD",
            "MERCH-THERMOMUG","MERCH-SHOPPER"
        }
        self.assertEqual({d.id for d in DRAFTS},expected)
        self.assertEqual(len(DRAFTS),16)
        canonical={t.id:t for t in define()}
        for d in DRAFTS:
            self.assertEqual(canonical[d.id].tz,d.tz)
            self.assertTrue(d.inputs)
            self.assertGreater(d.canvas_px[0],700)

    def test_svgs_contain_distinct_editable_vector_elements_and_disclaimer(self):
        distinct=set()
        for d in DRAFTS:
            xml=svg_for(d)
            root=ET.fromstring(xml)
            self.assertEqual(root.tag,"{"+SVG_NS+"}svg")
            self.assertEqual(root.attrib["{"+TZ_NS+"}status"],STATUS)
            self.assertEqual(root.attrib["{"+TZ_NS+"}dimensions-source"],
                             "PROVISIONAL_NOT_TZ_OR_PLATFORM_APPROVED")
            self.assertIn(TECH_NOTE,xml)
            self.assertNotIn("<script",xml)
            self.assertNotIn("<image",xml)
            self.assertNotIn("foreignObject",xml)
            self.assertNotIn("javascript:",xml)
            self.assertNotIn("href=",xml)
            ids={e.get("id") for e in root.iter()}
            self.assertTrue({"editable-background","editable-wireframe","draft-watermark","field-type"}.issubset(ids))
            if d.category=="merch":
                self.assertTrue({"editable-product-outline","imprint-safe","product-placeholder"}.issubset(ids))
                self.assertTrue(any((e.get("id") or "").startswith(("mockup-","editable-sticker-"))
                                    for e in root.iter()))
            if d.id.startswith("VK-RUBRIC"):
                self.assertTrue({"category-band","field-category","field-heading","image-placeholder"}.issubset(ids))
            distinct.add(xml)
        self.assertEqual(len(distinct),16)

    def test_png_previews_are_real_and_checksum_manifest_blocks_tampering(self):
        stats=verify(OUTPUT)
        self.assertEqual(stats["editable_svgs"],16)
        self.assertEqual(stats["png_previews"],16)
        self.assertEqual((stats["vk"],stats["website"],stats["merch"]),(6,1,9))
        self.assertEqual(stats["approved"],0)
        self.assertTrue(stats["all_dimensions_provisional"])
        manifest=json.loads((OUTPUT/"DIGITAL_MERCH_MANIFEST.json").read_text())
        self.assertEqual(manifest["museum_approvals"],0)
        self.assertEqual(manifest["final_merch_designs_created"],0)
        self.assertFalse(manifest["vk_size_platform_validated"])
        self.assertFalse(manifest["products_physical_dimensions_confirmed"])
        for d in DRAFTS:
            file=OUTPUT/f"TECH_{d.id}.png"
            self.assertEqual(_png_dims(file.read_bytes()),d.canvas_px)
            self.assertGreater(file.stat().st_size,5000)

    def test_modified_svg_preview_and_status_fail_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp)
            generate(folder)
            self.assertEqual(verify(folder)["approved"],0)
            svg=folder/"TECH_MERCH-STAMP.svg"
            svg.write_text(svg.read_text().replace(TECH_NOTE,"ОФИЦИАЛЬНЫЙ СТИЛЬ"))
            with self.assertRaisesRegex(ValueError,"modified editable SVG"):
                verify(folder)
            generate(folder)
            png=folder/"TECH_VK-RUBRIC-3.png"
            data=bytearray(png.read_bytes())
            data[-30]^=0x01
            png.write_bytes(data)
            with self.assertRaisesRegex(ValueError,"manifest"):
                verify(folder)
            generate(folder)
            mf=folder/"DIGITAL_MERCH_MANIFEST.json"
            mf.write_text(mf.read_text().replace(
                "ONLY_NEUTRAL_TECHNICAL_TEMPLATES_NOT_APPROVED","MUSEUM_APPROVED"))
            with self.assertRaisesRegex(ValueError,"manifest"):
                verify(folder)

    def test_missing_required_layout_and_invalid_raster_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp)
            generate(folder)
            (folder/"TECH_VK-COVER.png").unlink()
            with self.assertRaises(FileNotFoundError):
                verify(folder)
        with self.assertRaisesRegex(ValueError,"Invalid PNG"):
            _png_dims(b"not a PNG")
        with self.assertRaisesRegex(ValueError,"Invalid provisional"):
            svg_for(replace(DRAFTS[0],canvas_px=(100,100)))

    def test_reject_draft_as_official_design_evidence(self):
        # The evidence policy must stay strict if another kind of TECH_ asset
        # is introduced (now digital merch in addition to CP30/CP31).
        from scripts.audit_design_delivery import inventory
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            (root/"docs/tz-audit").mkdir(parents=True)
            (root/"docs/handoff").mkdir()
            (root/"docs/tz-audit/requirements.psv").write_bytes(
                (ROOT/"docs/tz-audit/requirements.psv").read_bytes())
            (root/"docs/handoff/DESIGN_EVIDENCE.csv").write_text(
                "id,path,museum_approval,notes\n"
                "VK-AVATAR,docs/design/technical-drafts/digital-merch/TECH_VK-AVATAR.svg,pending,wireframe\n")
            with self.assertRaisesRegex(ValueError,"cannot be design-delivery evidence"):
                inventory(root)


if __name__=="__main__":
    unittest.main()
