# Signed contract Spec Kit plan

**Implementation:** official Spec Kit v1.2.4, integration none; use existing project .specify scaffolding. Do not create second canonical roadmap or duplicate 325 statuses.

## Input and authentication

MacBook path: `~/Documents/Закупки/Музей хлеба/Договор` contains EIS export archive with supplier/customer detached signatures dated 21 and 23 October. Transfer entire archive **only** to the private Mac mini procurement area; never to the public repository. Public OOZ copied from MacBook competition documents, confirmed SHA-identical to EIS procurement OOZ. The signed PDF includes contract (pp1–14), OOZ (pp15–26), transfer-of-rights form (p27), price (p28), EIS signature display (p29).

## Method

- Hash full signed PDF and public OOZ, verify PDF structure of 29 pages.
- Generate in memory `pdftotext -layout`, mark all 1522 physical text lines with page/line, category, hash (no full signed text in repo).
- Extract each 124 numbered main-contract clauses to a position/first-line SHA. Do not mistake legal boilerplate or parties' rights for requested product functionality.
- Align original source OOZ tokens to signed PDF Annex 1 by ordered text matching; audit table reflow manually for TZ-148–150.
- Provide engineer-authored interpretation and evidence by contract clause, **not** a replacement for signed text.
- Verify map against source on Mac mini; GitHub CI only checks pinned map, known source identity and projections, never claims access to confidential signed PDF.
- Map technical and nontechnical issues to canonical `docs/ROADMAP.md` and existing TZ operational matrix.

## Stop-gates

No automatic acceptance, EIS signature trust assertion, rights transfer, new purchase obligation or promises of production compliance from manifest presence. Test lockfiles, privacy, legal dependencies, real firewalls and customer UAT independently.

## Rollback

The public DOCX contains only public procurement description and no signed certs. Signed archive remains private. Revert program/doc provenance if needed; no database/DNS/customer infrastructure affected.
