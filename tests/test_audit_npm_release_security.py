import copy
import unittest
from pathlib import Path
from importlib.util import module_from_spec, spec_from_file_location
p=Path(__file__).resolve().parents[1]/'scripts/audit_npm_release_security.py'
spec=spec_from_file_location('audit_npm_release_security',p)
a=module_from_spec(spec); spec.loader.exec_module(a)

class NpmReleaseAuditTests(unittest.TestCase):
    def setUp(self):
        self.prod={'vulnerabilities':{}}
        self.dev={'vulnerabilities': {name: {'severity':'high','via':['braces'], 'isDirect': name=='eslint-config-next'} for name in a.CHAIN}}
        self.dev['vulnerabilities']['braces']['via']=[{'url':a.ADVISORY}]

    def test_known_unpatched_dev_only_chain_is_monitored(self):
        self.assertEqual(a.validate(self.prod,self.dev)['dev_advisories'],5)
    def test_all_fixed_is_pass(self):
        self.assertEqual(a.validate(self.prod,{'vulnerabilities':{}})['dev_advisories'],0)
    def test_any_production_advisory_fails(self):
        with self.assertRaisesRegex(ValueError,'Production'):
            a.validate({'vulnerabilities': {'braces':{}}},self.dev)
    def test_new_dev_issue_fails(self):
        d=copy.deepcopy(self.dev);d['vulnerabilities']['new-package']={'severity':'high'}
        with self.assertRaisesRegex(ValueError,'Unexpected'):
            a.validate(self.prod,d)
    def test_second_braces_advisory_fails(self):
        d=copy.deepcopy(self.dev);d['vulnerabilities']['micromatch']['via']=[{'url':'https://advisory.invalid/new'}]
        with self.assertRaisesRegex(ValueError,'Additional'):
            a.validate(self.prod,d)
    def test_additional_braces_advisory_fails(self):
        d=copy.deepcopy(self.dev)
        d['vulnerabilities']['braces']['via'].append({'url':'https://advisory.invalid/additional'})
        with self.assertRaisesRegex(ValueError,'additional braces'):
            a.validate(self.prod,d)
    def test_unknown_root_advisory_fails(self):
        d=copy.deepcopy(self.dev);d['vulnerabilities']['braces']['via']=[{'url':'https://advisory.invalid/new'}]
        with self.assertRaisesRegex(ValueError,'Unrecognized'):
            a.validate(self.prod,d)
    def test_direct_dependency_expansion_fails(self):
        d=copy.deepcopy(self.dev);d['vulnerabilities']['braces']['isDirect']=True
        with self.assertRaisesRegex(ValueError,'Unexpected direct'):
            a.validate(self.prod,d)

if __name__ == '__main__': unittest.main()
