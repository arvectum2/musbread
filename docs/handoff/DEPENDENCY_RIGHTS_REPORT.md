# MusBread — CP-33D direct dependency and rights audit

**Not a full SBOM or legal approval.** Metadata in local lock files documents license declarations; it does not prove redistribution compliance or ownership.

| Component | Locked version | Declared license | Evidence | Delivery review |
|---|---|---|---|---|
| ezyang/htmlpurifier | v4.19.1 | LGPL-2.1-or-later | apps/cms/composer.lock | REQUIRED |
| laravel/framework | v13.36.0 | MIT | apps/cms/composer.lock | NOTICE_AND_COMPLIANCE_REQUIRED |
| moonshine/moonshine | 4.19.5 | MIT | apps/cms/composer.lock | NOTICE_AND_COMPLIANCE_REQUIRED |
| next | 16.4.1 | MIT | apps/web/package-lock.json | NOTICE_AND_COMPLIANCE_REQUIRED |
| react | 19.3.0 | MIT | apps/web/package-lock.json | NOTICE_AND_COMPLIANCE_REQUIRED |
| react-dom | 19.3.0 | MIT | apps/web/package-lock.json | NOTICE_AND_COMPLIANCE_REQUIRED |
| sanitize-html | 2.18.1 | MIT | apps/web/package-lock.json | NOTICE_AND_COMPLIANCE_REQUIRED |
| python-pptx | 1.0.2 | MIT | Installed python-pptx dist metadata on Mac mini; version pinned in requirements | VERIFY_EXACT_LICENSE_AND_NOTICES |
| pypdf | 5.6.1 | BSD family (classifier, exact version needs manual legal confirmation) | Installed pypdf dist metadata on Mac mini; version pinned in requirements | VERIFY_EXACT_LICENSE_AND_NOTICES |
| jodit/community-runtime | 4.18.4 | MIT | apps/cms/public/vendor/museum-jodit/LICENSE.txt; npm jodit@4.18.4 pinned SHA-256 | MIT_NOTICE_MUST_ACCOMPANY_DISTRIBUTED_ASSET |
| librsvg/native-rsvg-convert | SYSTEM_VERSION_NOT_PINNED | REQUIRES_NATIVE_PACKAGE_LICENSE_INVENTORY | Native Mac / Linux package outside locked application dependency tree | CONFIRM_NATIVE_TOOL_LICENSES_AND_DISTRIBUTION_BEFORE_DELIVERY |

## Mandatory legal and customer gates

- Jodit CE 4.18.4 MIT: retain author copyright and license notice in distributed copies
- HTMLPurifier LGPL-2.1-or-later: comply with notice, attribution and replacement rights
- Original source copyright ownership/contractor IP chain and third-party content is NOT audited
- Fonts and photos for customer-specific brand do not exist: actual licenses require documentation
- Native libre renderer build tools and transitive npm/composer dependencies need a full SBOM before delivery
- No library is transferred under exclusive Arvectum ownership; rights act must carve out all third party parts

## Interpretation

- Jodit CE 4.18.4 is a self-hosted, separately disclosed MIT-licensed WYSIWYG JavaScript editor.
- moonshine/tinymce and its GPL runtime are removed from the Composer lock and public CMS asset tree.
- pypdf's observed packaging classifier indicates BSD family; this report does not assert exact legally binding text. Verify installed LICENSE text.
- Fonts, logos, text, customer media and third-party services are not cleared by dependency locks.
- Avoid distributing vendor/node_modules in the public pre-award handoff. Official delivery must address whether/how such code is transferred.
- Reviewed direct dependencies only; transitive, browser bundled chunks and native binary provenance need a full SBOM.
