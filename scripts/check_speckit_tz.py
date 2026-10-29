#!/usr/bin/env python3
"""Spec Kit source gate: public projection + strictly private original verification."""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import re
import sys
import unicodedata
from zipfile import ZipFile
from xml.etree import ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FEATURE = ROOT / "specs/001-contract-tz-traceability"
MAP = FEATURE / "source-map.json"
SPEC = FEATURE / "spec.md"
ACCEPTANCE = FEATURE / "acceptance.md"
PSV = ROOT / "docs/tz-audit/requirements.psv"
ORIGINAL = Path("/Volumes/ArvectumSSD/Arvectum/data/tenders/eis/0372200172326000015/tz.txt")
SHA = "92c4db2a3f47988f4fc4c96b5ae652baa3faaa62a772e55a167c7cbaafb67420"
DOCX = ORIGINAL.with_suffix(".docx")
DOCX_SHA = "3e029344d179742632d519d4e425e6f8e9f757ce4df23e0419aa4302d4068536"
# Independent code-reviewed pin: changing a committed quote requires review of this script too.
PINNED_MAP_SHA = "798e45888eeb594192c1006c8a851d8fb275b2b472bc14579205c4d1a984d936"
COUNT = 325
LINES = 485

# Manually reviewed anchors for compound clauses where a naive lexical window
# can quote a true but irrelevant fragment (e.g. feedback instead of excursions).
# Every anchor MUST occur literally within one of its registry source lines.
FOCUSED_ANCHORS = {
    "TZ-005": "с надлежащим качеством",
    "TZ-019": "не должен копировать существующие логотипы",
    "TZ-020": "русская и английская версии",
    "TZ-032": "Главная страница стайта",
    "TZ-051": "пригласительного билета",
    "TZ-052": "благодарности",
    "TZ-053": "поздравительной открытки",
    "TZ-058": "соотношешение сторон 4:3, 16:9",
    "TZ-060": "футболка",
    "TZ-061": "термокружка",
    "TZ-066": ".ai, .eps, .svg",
    "TZ-069": ".pdf, .jpg, .png",
    "TZ-075": "единообразие в расположении",
    "TZ-081": "записи на экскурсию",
    "TZ-104": "каждый час или по событию",
    "TZ-140": "доступной среде",
    "TZ-174": "с выпадающими блоками",
    "TZ-180": "Поддержка форматов: текст",
    "TZ-182": "SVG, GIF",
    "TZ-195": "отдельного текстового блока",
    "TZ-231": "интуитивный интерфейс",
    "TZ-256": "в ручном режиме",
    "TZ-260": "единой сетки",
    "TZ-261": "Боковую панель",
    "TZ-262": "Нижний колонтитул",
    "TZ-264": "Разработка прототипа",
    "TZ-274": "Нагрузочное тестирование",
    "TZ-278": "Качество результата",
    "TZ-298": "устраняет неисправности",
}


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def physical_lines(raw: bytes) -> list[bytes]:
    # Python splitlines() splits the U+2028 inside this exact source and
    # corrupts contractual line pointers. Physical lines are LF ONLY.
    parts = raw.split(b"\n")
    if parts[-1] == b"":
        parts.pop()
    return parts


def references(span: str) -> list[int]:
    result = []
    for part in span.split(","):
        match = re.fullmatch(r"\s*(\d+)(?:-(\d+))?\s*", part)
        if not match:
            raise ValueError(f"Bad physical line span: {span!r}")
        start, end = int(match[1]), int(match[2] or match[1])
        if not 1 <= start <= end <= LINES:
            raise ValueError(f"Out-of-range span: {span!r}")
        result.extend(range(start, end + 1))
    if not result or len(set(result)) != len(result):
        raise ValueError(f"Empty/duplicate source line: {span!r}")
    return result


def registry() -> list[dict]:
    with PSV.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f, delimiter="^"))
    if len(rows) != COUNT or [r["ID"] for r in rows] != [
        f"TZ-{i:03d}" for i in range(1, COUNT + 1)
    ]:
        raise ValueError("Registry must have all 325 unique sequential TZ-IDs")
    for r in rows:
        references(r["Строки tz.txt"])
        if r["Фактически готово"] not in ("Да", "Частично", "Нет"):
            raise ValueError("Unexpected operational status: " + r["ID"])
    return rows


def original_lines() -> list[bytes]:
    if not ORIGINAL.is_file():
        raise ValueError(f"Private original unavailable: {ORIGINAL}")
    if not DOCX.is_file() or sha(DOCX.read_bytes()) != DOCX_SHA:
        raise ValueError("Original procurement DOCX missing or SHA-256 mismatch")
    raw = ORIGINAL.read_bytes()
    if sha(raw) != SHA:
        raise ValueError("FAIL-CLOSED: original SHA-256 does not match locked procurement source")
    parts = physical_lines(raw)
    if len(parts) != LINES:
        raise ValueError(f"Physical LF lines: {len(parts)}, expected {LINES}")
    return parts


def words(text: str) -> set[str]:
    return {w.lower() for w in re.findall(r"[^\W_]{4,}", text)}


def excerpt(lines: list[bytes], refs: list[int], atom: str, tz_id: str) -> tuple[int, int, str]:
    focus = FOCUSED_ANCHORS.get(tz_id)
    if focus is not None:
        for n in refs:
            line = lines[n-1].decode("utf-8-sig")
            pos = line.find(focus)
            if pos >= 0:
                start = min(max(0, pos - 22), max(0, len(line)-100))
                if start + 100 < pos + len(focus):
                    start = max(0, pos+len(focus)-100)
                return n, start, line[start:start+100]
        raise ValueError(f"Focused TZ excerpt anchor not present in cited originals: {tz_id}")
    target = words(atom)
    best = None
    for n in refs:
        t = lines[n - 1].decode("utf-8-sig")
        if not t.strip():
            continue
        starts = {0, max(0, len(t)-100)}
        for w in target:
            for m in list(re.finditer(re.escape(w), t, flags=re.IGNORECASE))[:5]:
                starts.add(max(0, min(m.start()-12, len(t)-100)))
        for start in sorted(starts):
            end = min(len(t), start+100)
            candidate = t[start:end]
            score = len(words(candidate) & target)
            key = (score, -len(t), -n, -start)
            if best is None or key > best[0]:
                best = (key, n, start, candidate)
    if best is None:
        # A purely blank line is an invalid human locator.
        raise ValueError("All cited source lines blank")
    return best[1], best[2], best[3]


def build_source_map(rows: list[dict], source: list[bytes]) -> dict:
    result = []
    for r in rows:
        refs = references(r["Строки tz.txt"])
        number, offset, quote = excerpt(source, refs, r["Атомарное обязательство"], r["ID"])
        result.append({
            "id": r["ID"],
            "clause": r["Пункт ТЗ"],
            "physical_lines": refs,
            "source_line_sha256": [sha(source[n-1]) for n in refs],
            "quote_line": number,
            "quote_offset": offset,
            "exact_excerpt": quote,
            "excerpt_is_full_clause": False,
            "atomic_registry_summary": r["Атомарное обязательство"],
        })
    return {
        "schema": 1,
        "authority": "original EIS procurement tz.txt; signed annex takes precedence",
        "source_sha256": SHA,
        "source_docx_sha256": DOCX_SHA,
        "source_physical_lf_lines": LINES,
        "original_in_public_git": False,
        "source_excerpt_warning": "Fragments are byte-verified navigational quotations, NOT full normative text.",
        "items": result,
    }


def render_spec(data: dict, rows: list[dict]) -> str:
    counts = {s: sum(r["Фактически готово"] == s for r in rows)
              for s in ("Да", "Частично", "Нет")}
    intro = f"""# Feature Specification — 325 obligations traceable to original TZ

**Status:** SOURCE-LOCKED SPECIFICATION BASELINE, not customer acceptance or site completion.
**Source:** EIS procurement 0372200172326000015, original §tz.txt§ in private Mac mini archive; **signed annex outranks this extract**.
**Original TXT SHA-256:** §{SHA}§; DOCX SHA-256: §{DOCX_SHA}§; **physical LF lines:** {LINES}.
**Existing operational ledger:** {counts['Да']} Да / {counts['Частично']} Частично / {counts['Нет']} Нет. Statuses are READ from §docs/tz-audit/requirements.psv§, not created or approved here.

## User stories and criteria

- **US1 / exact source (P0):** Every one of 325 rows links to an exact original clause, physical line, line SHA-256, quoted substring and the separately labelled engineering summary. The real full original text prevails over excerpts, summaries and decisions.
- **US2 / interpretation (P0):** Before changing a function read its whole original line and signed annex when applicable; mark unresolved readings, never silently lower requirements or invent additional obligations.
- **US3 / evidence (P0):** Local tests, UX studies, production network checks and museum stage approvals are independently necessary. Spec Kit does not change §docs/ROADMAP.md§ or mark contract milestones complete.
- **US4 / QA gate (P0):** CI enforces index integrity without private source; Mac mini verification checks the locked original byte-for-byte and each verbatim excerpt. Do not claim CI-only checks verify originals.

## Scope and evidentiary limits

This covers **325 DERIVED engineering atoms**, NOT 325 original numbered contractual clauses and NOT a reprint of the signed TZ. Each excerpt is literal and source-fingerprint-locked, but is often a **short part** of a compound clause. The «Engineering summary» column is an **existing interpretation**, not contractual text. For disputes the entire original line and original DOCX are required. One line may ground several atomic rows. No item changes status merely because it appears here.

**Separate implementation evidence/remaining work (not original TZ):** §acceptance.md§; **coverage of unreferenced original lines:** §source-coverage-review.md§.\n\n## Source-linked requirements\n\n| TZ-ID | Clause | Physical source lines | Exact excerpt (NOT full clause) | Existing engineering summary (NOT a quote) | Current status |
|---|---|---|---|---|---|
"""
    intro = intro.replace("§", chr(96))
    table = []
    for entry, row in zip(data["items"], rows):
        def cell(s: object) -> str:
            return str(s).replace("|", r"\|").replace("\n", " ↵ ").replace("\r", "")
        line_ids = ",".join(map(str, entry["physical_lines"]))
        table.append(f'| {entry["id"]} | {cell(entry["clause"])} | {line_ids} (quote L{entry["quote_line"]}) | {cell(entry["exact_excerpt"])} | {cell(row["Атомарное обязательство"])} | {cell(row["Фактически готово"])} |')
    outro = """
## How to check

- **Source verification on Mac mini:** §python3 scripts/check_speckit_tz.py --verify-source§
- **Offline CI structure/projection (NOT source verification):** §python3 scripts/check_speckit_tz.py --check§
- **After an approved status change in the existing registry:** §python3 scripts/check_speckit_tz.py --render§. This never rewrites the source-map.
- **Operational roadmap:** §docs/ROADMAP.md§, §docs/tz-audit/requirements.psv§.
- **Two VM architectural reading:** §docs/architecture/TZ_TWO_VM_VERBATIM_COMPLIANCE_20261029.md§.

**STOP:** Original SHA mismatch, missing signed annex attestation, unapproved real-person data, untested infrastructure or absent customer acceptance cannot be hidden by a green local spec check.
""".replace("§", chr(96))
    return intro + "\n".join(table) + "\n" + outro




def render_acceptance(data: dict, rows: list[dict]) -> str:
    """Existing operational evidence, NOT new contractual acceptance criteria."""
    lines = [
        "# Acceptance / evidence ledger — derived from existing operational register",
        "",
        "**IMPORTANT:** These are *our existing verification steps*, NOT quoted contractual acceptance",
        "conditions and NOT signed customer approval. Source of truth: original annex + real UAT.",
        "Exact TZ citation and excerpt: §spec.md§; authoritative full text: verified private original.",
        "Changes to evidence/needs/status in §requirements.psv§ require regenerating this projection.",
        "",
        "| ID | Priority | Current state | Existing evidence (engineering) | Remaining verification / delivery | Customer dependency |",
        "|---|---|---|---|---|---|",
    ]
    for entry, row in zip(data["items"], rows):
        def safe(value: object) -> str:
            return str(value or "—").replace("|", r"\|").replace("\n", " ↵ ").replace("\r", "")
        lines.append(
            "| " + " | ".join(safe(v) for v in (
                entry["id"], row["Приоритет"], row["Фактически готово"],
                row["Чекпоинт/доказательство"], row["Осталось выполнить"],
                row["Нужно от заказчика"]
            )) + " |"
        )
    lines += [
        "",
        "**NO-GO** until the museum-provided environment, the source contract, tested real results",
        "and relevant formal stage acceptance have been checked. An evidence row may be empty,",
        "incomplete, disputed or a plan rather than proof; it MUST NOT be auto-closed.",
        "",
    ]
    return "\n".join(lines).replace("§", chr(96))


def verify_docx_text_matches_source(data: dict, source: list[bytes]) -> int:
    # Ignore punctuation and typography without altering the normative original.
    def letters(text: str) -> str:
        return "".join(ch for ch in unicodedata.normalize("NFKC", text).casefold()
                       if ch.isalnum())
    with ZipFile(DOCX) as archive:
        tree = ET.fromstring(archive.read("word/document.xml"))
    tag = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t"
    text = letters("".join(node.text or "" for node in tree.iter(tag)))
    checked = 0
    last_position = 0
    refs = {line for item in data["items"] for line in item["physical_lines"]}
    for n in sorted(refs):
        fragment = letters(source[n-1].decode("utf-8-sig"))
        if len(fragment) < 12:  # short headings aren't reliable unique evidence
            continue
        found = text.find(fragment, last_position)
        if found < 0:
            raise ValueError(f"Original DOCX and derived TXT disagree or have inconsistent order at L{n}")
        last_position = found + len(fragment)
        checked += 1
    if checked < 250:
        raise ValueError(f"Too few substantive source lines verified against DOCX: {checked}")
    return checked



def expected_sections(clause: str) -> list[str]:
    if clause == "1.1–1.3":
        return ["1.1", "1.2", "1.3"]
    if clause.startswith("Приложение"):
        return ["appendix1"]
    return [part.strip().removeprefix("Раздел ") for part in re.split(r"[,/]", clause)]


def verify_source_section_links(data: dict, source: list[bytes]) -> int:
    active = ""
    section_at = {}
    for n, raw in enumerate(source, 1):
        line = raw.decode("utf-8-sig")
        numbered = re.match(r"^\s*(\d+(?:\.\d+)*)\.\s", line)
        section = re.match(r"^\s*Раздел\s+(\d+)\.", line)
        if numbered:
            active = numbered[1]
        elif section:
            active = section[1]
        elif "Приложение №1 к Описанию объекта закупки" in line:
            active = "appendix1"
        section_at[n] = active
    for item in data["items"]:
        actual = [section_at[n] for n in item["physical_lines"]]
        for expected in expected_sections(item["clause"]):
            if not any(a == expected or a.startswith(expected + ".")
                       for a in actual if a):
                raise ValueError(f"Clause mismatch: {item['id']} claims {expected}, source scopes {actual}")
    return len(data["items"])


def validate_map(data: dict, rows: list[dict], source: list[bytes] | None) -> None:
    if data.get("schema") != 1 or data.get("source_sha256") != SHA or data.get("source_docx_sha256") != DOCX_SHA or data.get("source_physical_lf_lines") != LINES:
        raise ValueError("Locked original identity or schema mismatch")
    items = data.get("items")
    if not isinstance(items, list) or len(items) != COUNT:
        raise ValueError("Source map must contain 325 items")
    for entry, row in zip(items, rows):
        if entry["id"] != row["ID"] or entry["clause"] != row["Пункт ТЗ"]:
            raise ValueError(f"ID or clause changed near {row['ID']}")
        if entry["atomic_registry_summary"] != row["Атомарное обязательство"]:
            raise ValueError(f"Engineering summary drift: {row['ID']}")
        refs = references(row["Строки tz.txt"])
        if entry["physical_lines"] != refs:
            raise ValueError(f"Wrong physical source references: {row['ID']}")
        hashes = entry["source_line_sha256"]
        if len(hashes) != len(refs) or not all(re.fullmatch("[0-9a-f]{64}", h) for h in hashes):
            raise ValueError(f"Invalid line SHA-256: {row['ID']}")
        n, offset, quote = entry["quote_line"], entry["quote_offset"], entry["exact_excerpt"]
        if n not in refs or not isinstance(offset, int) or offset < 0 or not quote or len(quote) > 100:
            raise ValueError(f"Invalid literal excerpt: {row['ID']}")
        focus = FOCUSED_ANCHORS.get(entry["id"])
        if focus is not None and focus not in quote:
            raise ValueError(f"Expected relevant anchored quote missing: {entry['id']}")
        if entry["excerpt_is_full_clause"] is not False:
            raise ValueError("Must not promote shortened excerpt to full original clause")
        if source is not None:
            for line, digest in zip(refs, hashes):
                if sha(source[line-1]) != digest:
                    raise ValueError(f"Original line mismatch: {row['ID']} L{line}")
            literal = source[n-1].decode("utf-8-sig")
            if literal[offset:offset+len(quote)] != quote:
                raise ValueError(f"Exact quote is not original substring: {row['ID']} L{n}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument("--bootstrap", action="store_true", help="Lock baseline once from private original")
    actions.add_argument("--verify-source", action="store_true", help="Verify original SHA, all line hashes and literal quotes")
    actions.add_argument("--check", action="store_true", help="Offline CI structure + projection ONLY (not source proof)")
    actions.add_argument("--render", action="store_true", help="Update projection after registry status change")
    actions.add_argument("--show", metavar="TZ-ID", help="Verify original and print exact full source lines for one TZ-ID")
    args = parser.parse_args()
    try:
        rows = registry()
        if args.bootstrap:
            if MAP.exists():
                raise ValueError("Baseline already exists: manual review needed, do not silently regenerate")
            original = original_lines()
            data = build_source_map(rows, original)
        else:
            if sha(MAP.read_bytes()) != PINNED_MAP_SHA:
                raise ValueError("Committed source-map changed; original-source review and explicit pin update required")
            data = json.loads(MAP.read_text(encoding="utf-8"))
            original = original_lines() if (args.verify_source or args.show) else None
        validate_map(data, rows, original)
        if original is not None:
            scoped = verify_source_section_links(data, original)
            matched = verify_docx_text_matches_source(data, original)
            print(f"Original source scopes: {scoped}/325 mapped clauses; DOCX match: {matched} substantive lines")
        projection = render_spec(data, rows)
        acceptance_projection = render_acceptance(data, rows)
        if args.bootstrap:
            MAP.write_text(json.dumps(data, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
            SPEC.write_text(projection, encoding="utf-8")
            ACCEPTANCE.write_text(acceptance_projection, encoding="utf-8")
        elif args.render:
            SPEC.write_text(projection, encoding="utf-8")
            ACCEPTANCE.write_text(acceptance_projection, encoding="utf-8")
        else:
            if SPEC.read_text(encoding="utf-8") != projection:
                raise ValueError("Spec projection drift: --render after approved status change")
            if ACCEPTANCE.read_text(encoding="utf-8") != acceptance_projection:
                raise ValueError("Acceptance evidence projection drift: --render after verified update")
        if args.show:
            match = next(((item, row) for item, row in zip(data["items"], rows)
                          if item["id"] == args.show), None)
            if match is None:
                raise ValueError("Unknown TZ-ID, expected TZ-001..TZ-325")
            entry, row = match
            print(f"Original TZ: {entry['id']} / clause {entry['clause']} / source SHA {SHA}")
            for line in entry["physical_lines"]:
                print(f"L{line:03d} [SHA {sha(original[line-1])[:16]}]: {original[line-1].decode('utf-8-sig')}")
            print(f"Separately derived engineering summary (NOT TZ quote): {row['Атомарное обязательство']}")
            print(f"Engineering status (NOT customer acceptance): {row['Фактически готово']}")
        check_mode = "SOURCE VERIFIED" if original is not None else "STRUCTURE ONLY (original NOT verified)"
        print(f"Spec Kit TZ PASS: {check_mode}, {COUNT} ID(s), {LINES} LF lines, SHA {SHA[:12]}...")
        return 0
    except (ValueError, KeyError, OSError, json.JSONDecodeError) as ex:
        print(f"Spec Kit TZ FAIL: {ex}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
