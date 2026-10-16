# CP-30D — editable print grid and PowerPoint templates

Date: 16 October 2026. Based on original procurement matrix TZ-038..042 (A2/A3/A4 printed carriers), TZ-054..058 (8 slide types, 4:3 and 16:9 including 4/6 text blocks), TZ-066..071 (editable formats and raster >=300dpi).

## Created and verified

- 13 editable SVG technical carrier layouts: 11 poster size variants and two price/hour signs. Separate trim/safe guides, crop marks, textual placeholders and image rectangles.
- 13 PDF previews with MediaBox matching the paper including preliminary 3 mm bleed, verified with pypdf.
- Two genuine editable OOXML PPTX presentations, 8 slide layouts each, in 4:3 and 16:9. Text blocks and vector shapes stay independent.
- PRINT_SPECS.md and TECHNICAL_MANIFEST.json with physical trim/artboard dimensions and FUTURE raster pixel requirements computed using ceil(mm*300/25.4).
- Script scripts/generate_technical_carriers.py with parameter validation, generated-output verification and negative unit tests. CI installs free python-pptx and pypdf; preview PDF generation uses native rsvg-convert on Mac mini, without Docker.

## Not ready, not accepted

- 3mm bleed and 10mm safe area are PROJECT ASSUMPTIONS, not requirements in original TZ and not approved by museum/print house.
- Vector SVG/PDF previews are not print-ready CMYK masters or actual 300dpi raster artwork.
- No approved brand, text, photos, font licensing, print proof, or client signature. Final AI/EPS/PSD/TIFF and legacy PPT (.ppt, not .pptx) not created.
- Native PowerPoint/Adobe open-edit-resave on museum machines and production printing are still manual.
- All 113 target positions remain unapproved; technical draft files are NOT entered as customer-approved design evidence in DESIGN_EVIDENCE.csv.

## Where to find materials

The generated, clearly marked technical materials and use instructions are in docs/design/technical-drafts. Original carrier requirements and customer inputs are traced in docs/handoff/DESIGN_DELIVERABLES.md and CUSTOMER_INTERVIEW_DESIGN_CHECKLIST.md.

Verify on Mac mini:
    /tmp/musbread-design-tools-venv/bin/python scripts/generate_technical_carriers.py --verify
    /tmp/musbread-design-tools-venv/bin/python -m unittest tests.test_generate_technical_carriers -q

Expenses 0 RUB. No Docker.
