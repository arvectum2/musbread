#!/usr/bin/env python3
"""Conservative pre-award delivery checklist from the tender matrix and files.

Prepared ≠ customer-accepted, legally transferable, deployable or finished.
Only existence of templates/source can be asserted without museum evidence.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

REQUIRED_PREAWARD = {
    "requirements_matrix": "docs/tz-audit/requirements.psv",
    "technical_requirements": "docs/REQUIREMENTS.md",
    "checkpoint_roadmap": "docs/CHECKPOINTS.md",
    "application_architecture": "docs/ARCHITECTURE.md",
    "threats_security": "docs/SECURITY.md",
    "licensing_risks": "docs/handoff/RIGHTS_MATRIX.md",
    "draft_transfer_act": "docs/handoff/ACT_RIGHTS_DRAFT.md",
    "draft_delivery_act": "docs/handoff/DELIVERY_ACT_DRAFT.md",
    "draft_final_report": "docs/handoff/FINAL_REPORT_TEMPLATE.md",
    "admin_guide_draft": "docs/handoff/ADMIN_GUIDE_TEMPLATE.md",
    "editor_guide_draft": "docs/handoff/EDITOR_GUIDE_TEMPLATE.md",
    "visitor_guide_draft": "docs/handoff/VISITOR_GUIDE_DRAFT.md",
    "handoff_integrity_script": "scripts/handoff_bundle.py",
    "content_accessibility_gate": "scripts/audit_accessibility_content.py",
    "design_inventory": "docs/research/CUSTOMER_ASSETS_REGISTER.csv",
    "customer_interview_brief": "docs/research/INTERVIEW_BRIEF.md",
    "ux_test_protocol": "docs/research/UX_PROTOCOL.md",
    "design_handover_catalog": "docs/handoff/DESIGN_DELIVERABLES.csv",
    "design_handover_checklist": "docs/handoff/DESIGN_DELIVERABLES.md",
    "museum_input_requests": "docs/handoff/CUSTOMER_INPUTS_AFTER_INTERVIEW.md",
    "design_source_evidence_registry": "docs/handoff/DESIGN_EVIDENCE.csv",
    "museum_interview_design_checklist": "docs/handoff/CUSTOMER_INTERVIEW_DESIGN_CHECKLIST.md",
    "secondary_carriers_specification": "docs/CP31_SECONDARY_TECHNICAL_CARRIERS.md",
    "secondary_carriers_readme": "docs/design/technical-drafts/secondary/README.md",
    "digital_merch_specification": "docs/CP32_DIGITAL_VK_MERCH_TEMPLATES.md",
    "digital_merch_readme": "docs/design/technical-drafts/digital-merch/README.md",
    "final_format_readiness": "docs/handoff/FINAL_FORMAT_READINESS.md",
    "dependency_rights_readiness": "docs/handoff/DEPENDENCY_RIGHTS_REPORT.md",
    "format_and_rights_protocol": "docs/CP33_FORMATS_RIGHTS_AUDIT.md",
    "full_locked_sbom": "docs/handoff/SBOM_CYCLONEDX.json",
    "full_locked_license_inventory": "docs/handoff/SBOM_LICENSES.csv",
    "full_locked_sbom_summary": "docs/handoff/SBOM_SUMMARY.md",
    "editor_replacement_decision": "docs/handoff/EDITOR_REPLACEMENT_DECISION.md",
    "sbom_editor_exit_protocol": "docs/CP34_SBOM_EDITOR_REPLACEMENT.md",
    "built_artifact_provenance": "docs/CP35_BUILT_ARTIFACT_PROVENANCE.md",
    "actual_build_delivery_gates": "docs/handoff/ACTUAL_DELIVERY_BUILD_GATES.md",
}

# Explicit, non-inferable real-world requirements: none can be marked
# complete by finding a filename or passing a unit test.
BLOCKERS = [
    ("formal_contract", "Signed contract, formal customer assignment, dates"),
    ("museum_interview", "In-person interview and confirmed brand/UX decisions"),
    ("approved_identity", "Museum-approved logos, brandbook, editable originals and fonts/licenses"),
    ("actual_customer_content", "Approved contacts, photos, documents, translations and rights"),
    ("public_ticketing", "Real ticket/visit integration, schedule and service acceptance"),
    ("lawful_applications", "PII operator, forms, 152-FZ/59-FZ applicability and secure workflow"),
    ("production_environment", "Real two-contour network, HTTPS/TLS, authorized credentials and backups"),
    ("production_av_cdr", "Museum-approved antivirus and conversion pipeline for files and XLS"),
    ("accessible_pdf", "All actual accessible documents, PDF-UA/ГОСТ evidence and alternatives"),
    ("manual_assistive_qa", "Screen reader, keyboard and native browsers with museum content"),
    ("ux_customer_tests", "Required real respondent sessions and museum feedback"),
    ("pentest", "Authorized independent test on museum-accepted target"),
    ("support_sla", "Production monitoring and 12-month support obligations"),
    ("third_party_rights", "Verified licensing and transferability, including TinyMCE"),
    ("editable_design_formats", "Approved AI/EPS/SVG/PSD/TIFF and PPT/PPTX outputs as required"),
    ("museum_approval", "Formal acceptance, signed acts and handover of media/documents"),
]


def inspect(root: Path) -> dict:
    matrix = root / REQUIRED_PREAWARD["requirements_matrix"]
    if not matrix.is_file():
        raise ValueError("Tender requirements matrix is unavailable")
    lines = matrix.read_text(encoding="utf-8").splitlines()
    head = lines[0].split("^")
    required = {"ID", "Фактически готово", "Учли в плане"}
    if not required.issubset(set(head)):
        raise ValueError("Tender matrix schema does not include required columns")
    rows = [dict(zip(head, line.split("^"))) for line in lines[1:] if line.strip()]
    ids = [row["ID"] for row in rows]
    if len(ids) != len(set(ids)) or len(rows) < 300:
        raise ValueError("Requirements matrix is incomplete or contains duplicate IDs")
    statuses = Counter(row["Фактически готово"] for row in rows)
    if any(key not in {"Да", "Частично", "Нет"} for key in statuses):
        raise ValueError("Unknown requirement implementation status")
    files = {}
    for name, relative in REQUIRED_PREAWARD.items():
        path = root / relative
        files[name] = {
            "path": relative,
            "status": "DRAFT_PRESENT_NOT_CUSTOMER_ACCEPTED" if path.is_file() else "MISSING",
        }
    blockers = [{"id": name, "status": "REQUIRES_CUSTOMER_OR_INDEPENDENT_EVIDENCE",
                 "description": detail} for name, detail in BLOCKERS]
    return {
        "purpose": "PREAWARD_INTERNAL_READINESS_ONLY",
        "production_ready": False,
        "customer_acceptance": False,
        "exclusive_rights_transferred": False,
        "tender_requirements": {
            "total": len(rows),
            "prototype_yes": statuses["Да"],
            "partial": statuses["Частично"],
            "not_implemented": statuses["Нет"],
            "warning": "Да means technical prototype status in local matrix, never acceptance.",
        },
        "prepared_files": files,
        "real_world_blockers": blockers,
        "summary": {
            "prepared_drafts": sum(v["status"].startswith("DRAFT_PRESENT") for v in files.values()),
            "missing_drafts": sum(v["status"] == "MISSING" for v in files.values()),
            "independently_unverified_requirements": len(blockers),
        },
    }


def markdown(report: dict) -> str:
    counts = report["tender_requirements"]
    summary = report["summary"]
    lines = [
        "# MusBread — pre-award delivery readiness review",
        "",
        "**Not a signed acceptance, completed contract or rights transfer.**",
        "",
        f"Requirements mapped: {counts['total']}; prototype yes: {counts['prototype_yes']}; "
        f"partial: {counts['partial']}; absent: {counts['not_implemented']}.",
        "",
        f"Prepared file/template locations: {summary['prepared_drafts']}; "
        f"missing: {summary['missing_drafts']}; external/manual gates: "
        f"{summary['independently_unverified_requirements']}.",
        "",
        "## Drafts and technical sources (existence only)",
        "",
        "| Artifact | Status | Path |", "|---|---|---|",
    ]
    lines += [
        f"| {key} | {value['status']} | {value['path']} |"
        for key, value in report["prepared_files"].items()
    ]
    lines += ["", "## Open acceptance, legal and museum dependencies", ""]
    lines += [
        f"- **{x['id']}** — {x['description']} ({x['status']})"
        for x in report["real_world_blockers"]
    ]
    lines += ["", "A passed CI or a file named '.pdf' does not prove accessibility, "
              "licensing, customer approval or production readiness.", ""]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--json", type=Path)
    parser.add_argument("--markdown", type=Path)
    parser.add_argument("--require-complete-drafts", action="store_true")
    args = parser.parse_args()
    report = inspect(args.root)
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    if args.markdown:
        args.markdown.parent.mkdir(parents=True, exist_ok=True)
        args.markdown.write_text(markdown(report))
    print("DELIVERY PREAWARD REVIEW:", report["summary"],
          "TENDER MATRIX:", report["tender_requirements"])
    return int(args.require_complete_drafts and report["summary"]["missing_drafts"] != 0)


if __name__ == "__main__":
    raise SystemExit(main())
