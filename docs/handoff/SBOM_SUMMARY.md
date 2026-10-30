# MusBread CP-34D — SBOM for all locked source dependencies

**Pre-award source dependency inventory, not a legal sign-off or installed-binary SBOM.**

| Package source | Entries |
|---|---:|
| Composer production | 82 |
| Composer development | 33 |
| npm all locked (including optional platform and dev) | 440 |
| Pinned design Python tools | 3 |
| Explicit embedded editor asset | 1 |
| Native build tool | 1 |
| **Total distinct component records** | **560** |

## Declared license risk buckets (one highest-priority bucket per component)

| Triage bucket | Count |
|---|---:|
| FILE_LEVEL_COPYLEFT_REVIEW | 3 |
| NON_STANDARD_OR_MANUAL_REVIEW | 2 |
| PERMISSIVE_NOTICE_CHECK | 537 |
| STRONG_COPYLEFT_OR_DUAL_REVIEW | 2 |
| UNKNOWN_REQUIRES_VERIFICATION | 1 |
| WEAK_COPYLEFT_LGPL | 15 |

Risk categories are triage signals, NOT legal conclusions. An SPDX OR alternative
does not force use of GPL; inspect original license and document chosen conditions.
Components may be optional on a target OS, build-only or dev-only.

## High-priority review

- Jodit Community is locally vendored under MIT; the copyright/license notice is mandatory.
- Composer nette/schema and nette/utils declare BSD-3-Clause OR GPL choices;
  review alternatives and notices, do not call them GPL-only.
- HTMLPurifier LGPL-2.1-or-later and platform-optional sharp/libvips
  declare LGPL-3.0-or-later and compound licenses in the Node lock.
- MPL-2.0 is present in axe-core and @axe-core/playwright test dependencies.
- BlueOak-1.0.0, CC-BY-4.0, native renderer and pypdf BSD notice require separate review.

Unresolved dependency graph references: **4**;
only optional peer targets remain, not missing locked mandatory runtime packages.

## Complete sources

- SBOM_CYCLONEDX.json: CycloneDX 1.6 all locked components and resolved graph.
- SBOM_LICENSES.csv: per-component source, exact declared license and triage.
- SBOM_SUMMARY.json: counted values, unmatched optional edges and limitations.

## Legal and delivery boundaries

- All locked Composer/npm production, dev and platform-optional records included.
- Two pinned Python design tools, bundled Jodit CE MIT and one native renderer disclosed.
- This does NOT establish an optional OS package is installed or distributed.
- Built vendored bundles, original license notices and transitive binaries still need inspection.
- Final deployment needs a new installed-binary artifact/SBOM comparison.
- Third-party exclusive rights are not owned by Arvectum.
- Museum-approved final design: 0/113.
