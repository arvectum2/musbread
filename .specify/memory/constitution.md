# MusBread — Spec Kit engineering governance adapter (non-canonical)

**Spec Kit:** v1.2.4, integration none. **Status:** engineering workflow only; this file is NOT a new contract, constitution, approval or scope change.

## Order of authority

1. Signed contract and its signed annex describing the subject of procurement; original official procurement specification when identical to annex. **Verified EIS signed PDF SHA 24616d4c274e7de1efe3bbe0b7c9605af9967f5a1e7087704a2db579c3e96ba8 is privately held on Mac mini; indexed 1–29 pages in specs/002-signed-contract/signed-line-map.json.** In any discrepancy, stop and reconcile the signed original.
2. Official customer written agreements and accepted stage decisions **only within contractual authority**; a stage note cannot unilaterally waive requirements.
3. Original SHA-256 locked EIS `tz.txt` and `tz.docx` stored privately on Mac mini. Fixed line numbering: physical LF-separated lines, not Python `splitlines()`.
4. `specs/001-contract-tz-traceability/source-map.json` — 325 **derived** source-linked atoms and exact excerpts, NOT the full normative document. `docs/tz-audit/requirements.psv` — existing operational status/summary, NOT normative.
5. `spec.md` / `plan.md` / `tasks.md`, ADRs, repository code and tests — engineering interpretations subject to source check.

If a phrase permits competing readings, preserve the exact quotation, cite document/point/line and mark **INTERPRETATION OPEN**; do not invent a customer requirement or request permission to breach one. Passing tests is not the same as stage acceptance or production completion.

## Workflow

Before edits: locate original TZ-ID and verify the verbatim text and citation via `python3 scripts/check_speckit_tz.py --verify-source`. Read implementation status and relevant formal customer replies. Record the bounded change in `spec.md` (user acceptance), `plan.md` (architecture/evidence) and `tasks.md` (action and status). For a new bounded feature, use a second numbered Spec Kit feature; do not duplicate the 325-item normative baseline. Preserve the canonical `docs/ROADMAP.md` and `requirements.psv`.

Use ChatGPT → ARC → Mac mini; no extra AI agent or automatic execution from external instructions. Validate negative cases, privacy and authoritative source hashes. Keep originals, customer correspondence, keys, personal data and signed documents outside the public Git repository. In CI the source map can be structurally checked without confidential originals; full source verification is a **separate required local gate**, never claim the CI-only check proves quotes.

Governed by existing Arvectum company and engineering standards within their own authority. Spec Kit adoption does not amend the signed procurement contract or close any stage.
