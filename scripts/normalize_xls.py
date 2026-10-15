#!/usr/bin/env python3
"""Read legacy OLE2 XLS as VALUES ONLY and emit a minimal macro-free XLSX.

This is a developer-only conversion stage. It does NOT perform malware/AV
scanning and is blocked for production requests pending museum approval.
No macros, formulas, hyperlinks or objects from the original workbook survive.
"""
import argparse
from datetime import date, datetime
import math
import os
from pathlib import Path
import re
import sys
import zipfile
from xml.sax.saxutils import escape, quoteattr

import xlrd

MAX_INPUT = 5 * 1024 * 1024
MAX_SHEETS = 12
MAX_ROWS = 10000
MAX_COLUMNS = 128
MAX_CELLS = 50000
MAX_TEXT = 10000
OLE_HEADER = bytes.fromhex("D0CF11E0A1B11AE1")


def safe_text(value):
    """Raise on XML 1.0-forbidden control characters, do not reinterpret formulas."""
    text = str(value)
    if len(text) > MAX_TEXT or any(
        (ord(char) < 32 and char not in "\t\n\r")
        or ord(char) in (0xFFFE, 0xFFFF)
        for char in text
    ):
        raise ValueError("Unsupported control characters or long cell")
    return text


def column_letter(index):
    result = ""
    index += 1
    while index:
        index, rem = divmod(index - 1, 26)
        result = chr(65 + rem) + result
    return result


def cell_xml(cell, address, datemode):
    kind = cell.ctype
    if kind in (xlrd.XL_CELL_EMPTY, xlrd.XL_CELL_BLANK):
        return ""
    if kind == xlrd.XL_CELL_ERROR:
        # Never create an Excel error cell that can be confused with a formula.
        text = "[Original spreadsheet error]"
    elif kind == xlrd.XL_CELL_DATE:
        text = safe_text(xlrd.xldate_as_datetime(cell.value, datemode).isoformat(sep=" "))
    elif kind == xlrd.XL_CELL_BOOLEAN:
        text = "TRUE" if cell.value else "FALSE"
    elif kind == xlrd.XL_CELL_NUMBER:
        number = float(cell.value)
        if not math.isfinite(number):
            raise ValueError("Invalid spreadsheet numeric value")
        return '<c r=' + quoteattr(address) + ' t="n"><v>' + format(number, ".15g") + '</v></c>'
    else:
        text = safe_text(cell.value)
    # Inline string is never evaluated by Excel as an executable formula.
    return '<c r=' + quoteattr(address) + ' t="inlineStr"><is><t xml:space="preserve">' + escape(text) + '</t></is></c>'


def convert(input_path: Path, output_path: Path):
    if input_path.stat().st_size < 128 or input_path.stat().st_size > MAX_INPUT:
        raise ValueError("Invalid XLS size")
    with input_path.open("rb") as file:
        if file.read(8) != OLE_HEADER:
            raise ValueError("Not an OLE2 XLS container")
    book = xlrd.open_workbook(str(input_path), on_demand=True, ragged_rows=False)
    if not 1 <= book.nsheets <= MAX_SHEETS:
        raise ValueError("Sheet count limit exceeded")

    sheets = []
    names = []
    total_cells = 0
    for sheet_number in range(book.nsheets):
        sheet = book.sheet_by_index(sheet_number)
        if sheet.nrows > MAX_ROWS or sheet.ncols > MAX_COLUMNS:
            raise ValueError("Sheet dimensions exceed read-only preview limit")
        names.append(safe_text(sheet.name))
        rows = []
        for row_index in range(sheet.nrows):
            cells = []
            for column_index in range(sheet.ncols):
                cell = sheet.cell(row_index, column_index)
                if cell.ctype in (xlrd.XL_CELL_EMPTY, xlrd.XL_CELL_BLANK):
                    continue
                total_cells += 1
                if total_cells > MAX_CELLS:
                    raise ValueError("Too many nonempty cells")
                address = column_letter(column_index) + str(row_index + 1)
                cells.append(cell_xml(cell, address, book.datemode))
            if cells:
                rows.append('<row r="' + str(row_index + 1) + '">' + ''.join(cells) + '</row>')
        sheets.append('<?xml version="1.0" encoding="utf-8"?>'
                      '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
                      '<sheetData>' + ''.join(rows) + '</sheetData></worksheet>')
    book.release_resources()

    content_types = ['<?xml version="1.0" encoding="utf-8"?>',
                     '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">',
                     '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>',
                     '<Default Extension="xml" ContentType="application/xml"/>',
                     '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>']
    relationships = ['<?xml version="1.0" encoding="utf-8"?>',
                     '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">']
    workbook_sheets = []
    for i, name in enumerate(names, 1):
        content_types.append('<Override PartName="/xl/worksheets/sheet' + str(i)
                             + '.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>')
        relationships.append('<Relationship Id="rId' + str(i)
                             + '" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet"'
                             + ' Target="worksheets/sheet' + str(i) + '.xml"/>')
        workbook_sheets.append('<sheet name=' + quoteattr(name) + ' sheetId="' + str(i) + '" r:id="rId' + str(i) + '"/>')
    content_types.append('</Types>')
    relationships.append('</Relationships>')
    workbook = ('<?xml version="1.0" encoding="utf-8"?>'
                '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'
                ' xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
                '<sheets>' + ''.join(workbook_sheets) + '</sheets></workbook>')
    root_rels = ('<?xml version="1.0" encoding="utf-8"?>'
                 '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                 '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument"'
                 ' Target="xl/workbook.xml"/></Relationships>')
    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zipout:
        zipout.writestr("[Content_Types].xml", "".join(content_types))
        zipout.writestr("_rels/.rels", root_rels)
        zipout.writestr("xl/workbook.xml", workbook)
        zipout.writestr("xl/_rels/workbook.xml.rels", "".join(relationships))
        for i, xml in enumerate(sheets, 1):
            zipout.writestr("xl/worksheets/sheet" + str(i) + ".xml", xml)
    if output_path.stat().st_size > 15 * 1024 * 1024:
        raise ValueError("Normalized workbook exceeds size limit")
    print("Converted sheets=%s cells=%s; original formulas/macros/objects not preserved" %
          (len(sheets), total_cells))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        convert(args.input, args.output)
    except Exception as error:
        try:
            args.output.unlink(missing_ok=True)
        except OSError:
            pass
        print("XLS conversion rejected: " + str(error), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
