# Implementation Plan — source-locked specification for MusBread

**Date:** 2026-10-29
**Spec Kit:** 1.2.4, `none`, `sh`, same pattern as Tender Agent PR #520
**Baseline:** procurement 0372200172326000015, private `tz.txt`/`tz.docx`, SHA-256 `92c4db2a3f47988f4fc4c96b5ae652baa3faaa62a772e55a167c7cbaafb67420`
**Authority:** signed contract annex supersedes any derivative; primary extracted TXT is a checked locator.

## Phase A — reproducible source mapping

Initialize Spec Kit (no external coding assistant), governance adapter and 325-atom exact-source index. Preserve `requirements.psv` as the only operational status ledger and the existing roadmap. No source copy in public Git: anchor normalized verbatim snippets by physical original line and SHA-256 of exact LF-separated line bytes.

For each atom generate: TZ-ID, exact original clause reference, physical source line numbers, SHA-256 of each referenced line, one verbatim excerpt with source line and full source line length, and the *separate* existing atomic engineering summary. A short excerpt (maximum 100 characters per atom) is navigation evidence, **not** a complete verbatim replacement of an entire source clause; when unsure open the whole source line. Reject ambiguous references, duplicates, hash drift or truncated files.

## Phase B — enforceable gates

`python3 scripts/check_speckit_tz.py --verify-source`: mandatory on Mac mini before interpreting a new requirement; checks pinned SHA, 485 LF lines, all referenced line digests and every excerpt character against the source; checks all 325 source-clause scopes and 263 substantive cited lines against the original DOCX after whitespace/typography normalization; validates generated spec and complete 325-ID registry.

`python3 scripts/check_speckit_tz.py --check`: CI-safe offline check of exact projection, structure, 325 IDs, status snapshot and hashes; **does not establish source authenticity without original files**. Add fail-fast unit tests for bad IDs, references, tampering and original LF/Unicode lines, and include offline check in the existing quality workflow. Do not change statuses in `requirements.psv` by this operation.

## Phase C — spec-driven project execution

Before any architectural change cite TZ-ID and original quote, distinguish explicit requirement from assumption and approved customer decision. Record code/QA/UAT evidence with statuses in canonical roadmap, not a second green/red system. Slices: brand/interview, CMS/publication and two-VM isolation, interactions/integrations, accessibility/UX, handover/acceptance. Pending museum infrastructure and privacy approvals remain blocked.

## Risks and rollback

- `str.splitlines()` treats embedded U+2028 as a line separator, shifting physical numbering. Always split on LF only.
- Original procurement TZ may differ from **signed annex**: treat discrepancy as a blocked verification, never silently assume equivalence.
- `requirements.psv` summaries may omit a conjunctive obligation; a passing summary checker is no substitute for opening exact source.
- Public CI cannot access private original; do not print whole original text into public logs or commit original DOCX/TXT.
- Revert the isolated new Spec Kit files/CI step if needed; no DB migrations, live deployments, DNS or customer communication.
