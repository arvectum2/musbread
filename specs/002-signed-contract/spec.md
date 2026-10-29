# Feature Specification — signed contract, Annex 1 OOZ and Annex 2 price

**Created:** 2026-10-30. **Status:** Signed source verified for text and page provenance; technical compliance remains IN PROGRESS.
**Normative source:** Signed PDF exported from EIS archive on MacBook, 29 pages, privately stored on Mac mini. Signed source SHA-256: `24616d4c274e7de1efe3bbe0b7c9605af9967f5a1e7087704a2db579c3e96ba8`.
**Competition OOZ public copy:** `docs/contract/OOZ_EIS_0372200172326000015.docx`; SHA-256 `3e029344d179742632d519d4e425e6f8e9f757ce4df23e0419aa4302d4068536`.
**Source priority:** Signed PDF and formal EIS record > procurement original OOZ > engineering TZ-001...TZ-325 mapping > internal technical ADRs.

## User scenarios and acceptance

- **US1 — Signed-source identity (P0):** Reviewer opens the actual signed contract through approved local private path and can locate any of 1522 extracted lines by PDF page, number and hash; original pages, layout and dates are authoritative, not the extracted strings.
- **US2 — Complete contract reading (P0):** All 124 independently numbered substantive contract clauses have source locators, including contractor's obligations, scheduling, acceptance, security, IP, payments and warranty; no clause is silently reduced to an engineering checklist.
- **US3 — Signed Annex 1 mapping (P0):** All 325 derived original TZ atoms have locators within the signed PDF's Annex 1; 322 lexical sequence alignments and three independently checked table-reflow headings. Every quoted original condition is interpreted with the complete signed context.
- **US4 — Signed Annex 2 price (P0):** Show 24,050.52 RUB website + 14,949.48 RUB identity = 39,000 RUB total, excluding VAT as written; prohibit silently inventing a separate customer-chargeable scope.
- **US5 — Real acceptance evidence (P0):** Contractual due dates and EIS submission workflow are separated from internal code and QA; no automated test or Spec Kit manifest marks a customer act signed.
- **US6 — Safe originals (P0):** Only public original OOZ DOCX, provenance hashes and sanitized engineer-authored summaries are in Git. Never commit signed PDF containing individual identifiers, financial details, signature binaries or internal correspondence.

## Mandatory signed-original facts

See `source-audit.md` for the full categorized clause crosswalk, prices and deadlines; `signed-line-map.json` holds all 1522 line pointers, 124 independent clause IDs, 325 TZ-to-signed-PDF positions. The source is **29-page signed PDF**, not the procurement draft; an original PDF line/page must be opened for any contested legal obligation.

### Boundaries

- This does not validate cryptographic chains of the EIS detached .sig certificates. Signing dates are as recorded in the EIS PDF.
- Original competition OOZ DOCX and existing TZ have identical file SHA. The signed PDF's text reproduces the OOZ with table reflow; corresponding token alignment is ≈99.65%, not byte-equivalence between unlike formats.
- 325 atoms are *our* decomposition, not 325 separate signed numbered clauses. Formal contract has 124 numbered clauses captured in the main contract segment.
- On a conflict signed source has precedence, and remediation is documented without quiet change to the customer agreement.
- Real production two-VM access, release pipeline, client acceptance, licencing and rights transfer are separate gates. Existing no-go remains.

## Workstream handoff

1. Full signed source contract audit + source-mapped hash check.
2. Architecture and content/integration audit against original TZ.
3. Targeted repository refactors with fail-first tests; preserve strict 2-VM requirement, never introduce third host or public CMS.
4. Production, legal and customer acceptance on actual infrastructure.
