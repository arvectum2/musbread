# TZ-115…TZ-174: header, accessible mode, contacts, visitor directions, sticky nav

16–17 October 2026. Source: ЕИС закупка 0372200172326000015, ООЗ приложение 3, primary `docs/tz-audit/requirements.psv`. Every feature listed below was explicitly checked against the listed TZ-ID/line **before code modifications**. Pre-contract UI remains demonstrational, no actual museum sign-off.

| TZ (primary line) | Observed, verified technical state | Remaining condition for `Да` |
|---|---|---|
| 115 (170) | Seven contract top-level categories in desktop `SiteHeader` and mobile menu, real nested CMS child hierarchy from recent TZ-072/076, explicit Playwright both screen sizes | Museum-approved complete structure, UAT |
| 117 (171) | `VisionMode`: large text (1.25×), contrasting white/black background and foreground, underlined links, focus indicators, toggle with `aria-pressed`, saved preference after reload and between pages. Fixed main caption contrast and 320 px overflow uncovered by E2E. Automated `axe-core` WCAG 2.1 A/AA sweep: four actual public routes (home, contacts, accessibility, search), no serious/critical findings after fix. | Approved accessible design/standards, manual screen reader, Safari/mobile checks with users; 4-page automated sweep is not full WCAG certificate |
| 118 (171) | An unambiguous link/button-style control **«Доступная среда»** exists in header at 320, 390, 768, 960, 1024, 1440px, not hidden by CSS. Correct `/guide/accessible-museum/` page and outbound reference to actual museum accessible-visitor information; no fictional accessible entrance details | Actual museum accessibility passport and UAT |
| 120 (172) | Header `GlobalSearch` button and full-page search in previous commit; unchanged by these responsive adaptations | Real CMS content, binary text extraction evaluation, museum sign-off |
| 125 (177) | Footer visibly includes sourced postal address, phone, email, opening hours, closed/sanitary day, and explicit pre-approval note | Confirm all factual contact values and hours with museum |
| 126 (178) | Footer has source-identified current privacy-policy URL. **We did not generate a substitute legal text for the museum.** | Official updated signed legal document/consent policy and publication approval |
| 134 (187) | CMS `MuseumEntry` type `document`, signed content-addressed PDF/DOCX/XLSX downloads and public document listing templates exist | Actual official document list/files, versions, copyright/accessibility review |
| 138 (191) | Working public `/guide/museum-contacts/`: sourced address, email, phone, opening schedule, nearby station and **external map address search**, no unverified geographic pin nor map iframe/third-party tracking. Link to accessibility page and actual museum accessibility source | Confirm current official contacts, map specifics and accessible entrance; staff UAT |
| 139 (192–198) | `/guide/plan-visit/`: opening-hours, contacts, transport hint, map lookup, disability accessibility links; text remains clearly a provisional source copy | Current rules/ticket policies/schedules, visitor flow validation |
| 142 (194) | Official external refund-policy URL remains in footer and guide site links; **not** copied, extended or changed to invent ticket operator terms | Approved museum/merchant rules and responsible contact |
| 173 (231) | Sticky `.site-header`; verified anchored after 950 px vertical scroll in Playwright and reachable by keyboard | Approved full navigation tree and real-browser UAT |
| 174 (231) | Native keyboard-capable `<details><summary>` mega dropdown (7 categories), support for CMS deeply nested hierarchy, tested via focus→Enter→link→Enter | Approved full navigation tree and UAT incl. assistive tech |

## E2E and non-goals

- `apps/web/e2e/header-a11y-tz.spec.ts`: 7 sections both desktop/mobile; visible access controls across **six** viewport widths (down to 320px), 1.25× type, persisted state, header axe-core accessibility.
- `apps/web/e2e/visitor-info-tz.spec.ts`: contacts link, map address-only search, sourced factual footer, accessibility info and sticky keyboard menu.
- `apps/web/e2e/a11y-coverage-tz.spec.ts`: WCAG 2.1 A/AA serious/critical check across four public routes in vision mode. Fix for first run's low-contrast main caption recorded.
- Existing Next.js lint/static export and Playwright browser suite; no new packages, runtime network calls, cookies, CMS access or changes to TinyMCE.
- No legal documents created, no fabricated museum contacts or accessible routing guarantees. External map opens with `noopener noreferrer` and submits entered reference address only **if the visitor activates the link**.

**Statuses** remain `Частично` where applicable, because the actual museum has not reviewed or accepted these pages and policies. Items with exhausted current local scope are moved from immediate queue to explicit external-blocker status, while binary-document search (TZ-120) remains available for technical work.
