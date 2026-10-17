"""Fail-closed proof for legal audit; no real museum personal data."""
from __future__ import annotations
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('audit_legal_readiness',ROOT/'scripts/audit_legal_readiness.py')
assert spec and spec.loader
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class LegalReadinessTest(unittest.TestCase):
    def test_all_thirteen_legal_requirements_and_twelve_disclosures_are_pending(self):
        audit=mod.inspect(ROOT)
        self.assertEqual(audit['requirements_total'],325)
        self.assertEqual(audit['legal_ids_checked'],13)
        self.assertEqual(len(audit['disclosure_register']),12)
        self.assertFalse(audit['legal_ready'])
        self.assertFalse(audit['may_activate_appeals'])
        self.assertFalse(audit['may_activate_real_pii_intake'])
        self.assertFalse(audit['may_claim_pdf_ua_conformity'])
        self.assertTrue(all(not x['compliance_approved'] for x in audit['legal_controls']))
        self.assertTrue(all(not x['accepted_by_museum'] for x in audit['disclosure_register']))
        self.assertEqual(set(mod.REFERENCE),{x['id'] for x in audit['legal_controls']})
        for law in ('TZ-279','TZ-280','TZ-281'):
            row=next(x for x in audit['legal_controls'] if x['id']==law)
            self.assertFalse(row['compliance_approved'])
            self.assertIn('UNDECIDED' if law=='TZ-279' else
                'NOT accepted' if law=='TZ-280' else 'must be confirmed',
                row['verified_technical_scope'])
            self.assertIn('https://',row['reference_url'])
        self.assertFalse(audit['signals']['telecom_operator_status_confirmed'])
        self.assertFalse(audit['signals']['state_security_law_applicability_approved'])
        self.assertTrue(audit['signals']['default_public_pii_intake_disabled'])

    def test_unknown_documents_or_source_links_never_flip_compliance(self):
        audit=mod.inspect(ROOT)
        self.assertIn('юридическая',mod.markdown(audit).lower())
        self.assertIn('НЕ юридическое заключение',mod.markdown(audit))
        self.assertIn('TZ-283',mod.markdown(audit))
        self.assertIn('TZ-290',mod.markdown(audit))
        for row in audit['disclosure_register']:
            self.assertFalse(row['official_signed_document_verified'])

    def test_invalid_requirement_registry_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            base=Path(folder)
            (base/'docs/tz-audit').mkdir(parents=True)
            (base/'docs/tz-audit/requirements.psv').write_text('ID^Фактически готово\nTZ-278^Да\n',encoding='utf-8')
            with self.assertRaises(ValueError):mod.inspect(base)

if __name__=='__main__':unittest.main()
