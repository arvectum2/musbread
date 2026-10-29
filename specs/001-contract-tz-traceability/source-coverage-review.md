# Independent original-TZ coverage check — 2026-10-30

**Scope:** original EIS procurement TZ 0372200172326000015, private original TXT/DOCX with the pinned SHA-256 from the source map; **not** signed-contract annex acceptance.

## Coverage is of the actual original, not of our derived register

- Original TXT: 485 **physical LF lines**, including blank lines, front matter, headings and signature templates.
- Referenced by 325 *derived* TZ atoms: 290 distinct physical lines.
- Not directly referenced: 195 lines, consisting of 108 blank, 75 short non-empty and 12 long non-empty.
- The 75 short non-empty unreferenced lines were manually classified as title/section headings, column labels, signatures, letterheads, and other formal scaffolding, not standalone unmodelled functional requirements.
- Of the 12 long non-empty unreferenced lines: 10 are headings/introductions to groups whose individual obligations are linked; original L31 is the procurement SME participation preference, already covered in the composite procurement metadata atom TZ-001; L400 is a signed-form role/name, not a new site requirement.

| Physical original line | Review of the unreferenced longer line | Decision |
|---|---|---|
| L31 | 44-FZ SME-only participation procurement statement | Covered as procurement identification in TZ-001; not a site feature |
| L93 | Introduction to required branded carrier layouts | Specific carriers covered TZ-032 onward |
| L138 | Introduction to access roles | Visitor/editor/admin mapped TZ-080 onward |
| L147–148 | Title and introduction to two-contour architecture | Concrete requirements TZ-099 onward |
| L160 | Availability and universal design section title | Specific obligations mapped |
| L230 | Navigation principles introduction | Specific navigation requirements mapped |
| L315 | Process/stages introduction | Stage details mapped |
| L323 | Stage approval introduction | Individual stages mapped |
| L351 | Warranty section heading | Warranty requirements mapped |
| L396 | Exclusive rights transfer form heading | Rights and handover mapped |
| L400 | Authorized role and person's name in annex form | Formal role/template, not a new technical requirement |

**Verdict for the source-list audit only:** no independent substantive requirement missing from 325-atom coverage in these **unreferenced** original lines. This is *not* a claim that 325 human summaries are semantically perfect or individually satisfy the signed contract: one LF line can contain several conditions, alternatives, exceptions and acceptance thresholds; their decomposition and formal interpretation must be reviewed in context. The source map proves citations and identity, not legal compliance.

**High-risk deviation:** The original L157 says `каждый час или по событию`, not that both are independently obligatory. Our operational atoms TZ-104 / TZ-105 split it for engineering tracking. Keep both implementation modes available if useful, but do not misrepresent a conjunction as the contractual wording. The actual signed annex is still to be independently checked.

**Code quality caution:** A literal 100-character excerpt can be correctly quoted yet irrelevant to its atom. The anchor review corrected selected priority examples (TZ-081, TZ-104, TZ-019, TZ-260/261, etc.) and the full-line `--show TZ-NNN` command remains the required way to resolve ambiguous readings. This audit does not certify every paraphrase as semantically equivalent.

**Status:** coverage review completed; signed-annex equivalence and contractual acceptance pending.
