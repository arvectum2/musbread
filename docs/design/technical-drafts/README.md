# CP-30D: editable technical carrier drafts, not approved design

These files are neutral pre-award grids, NOT museum-approved identity, artwork, print-ready masters, legal rights transfer, or fulfilled TZ design deliverables.

Generated: 13 editable SVG (11 paper poster combinations A2/A3/A4 and two A4/A3 price/hour signs), 13 vector PDF previews, two OOXML PowerPoint decks each containing eight editable slide types in 4:3 and 16:9.

Original TZ specifies A2/A3/A4, 300 dpi print raster output, and PowerPoint slide types/ratios. Default 3 mm bleed and 10 mm safe margin are PROPOSED values, NOT confirmed by museum or printer.

A4 trim 210x297 mm, proposed full artboard 216x303 mm.
A3 trim 297x420 mm, proposed full artboard 303x426 mm.
A2 trim 420x594 mm, proposed full artboard 426x600 mm.

SVG uses independent editable text nodes, guides, crop marks, placeholders and vectors. PDF previews are vector/RGB, NOT final CMYK masters. PowerPoint deck slide elements are separate editable OOXML text/shape objects, not full-page bitmaps. Legacy .ppt is not provided.

TECHNICAL_MANIFEST.json and PRINT_SPECS.md contain the exact geometry and calculated pixel counts for FUTURE 300dpi raster files. No actual raster print originals are made by this step.

Regenerate from project root with the native tools:
    /tmp/musbread-design-tools-venv/bin/python scripts/generate_technical_carriers.py --with-pdf-previews
    /tmp/musbread-design-tools-venv/bin/python scripts/generate_technical_carriers.py --verify

Before any printing: confirm actual print house bleed, safe area, color/CMYK, paper, full-resolution images and licenses, artwork, fonts, crop marks, approved content, sizes, legal rights and customer sign-off. Final AI/EPS/PSD/TIFF/PPT/PPTX and actual .ppt editing tests remain separate work.

All 113 target positions in DESIGN_DELIVERABLES.csv are still without customer-approved design.
