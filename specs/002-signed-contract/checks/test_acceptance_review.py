import importlib.util,unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location("gate",Path(__file__).with_name("check_acceptance_review.py"))
gate=importlib.util.module_from_spec(spec);spec.loader.exec_module(gate)
class Cases(unittest.TestCase):
    def setUp(self):self.d,self.o,self.c=gate.inputs()
    def test_valid(self):self.assertEqual(gate.validate(self.d,self.o,self.c),[])
    def test_lost_tz(self):self.d["tz"].pop();self.assertTrue(gate.validate(self.d,self.o,self.c))
    def test_lost_section(self):self.d["clauses"].pop();self.assertTrue(gate.validate(self.d,self.o,self.c))
    def test_old_status_not_proof(self):self.d["tz"][0]["review_state"]="verified";self.assertTrue(gate.validate(self.d,self.o,self.c))
    def test_native_status_drift(self):self.d["tz"][0]["source_status"]="changed";self.assertTrue(gate.validate(self.d,self.o,self.c))
    def test_source_drift(self):self.c[next(iter(self.c))]+=b"\n";self.assertTrue(gate.validate(self.d,self.o,self.c))
    def test_wrong_perspective(self):
        r=self.d["clauses"][0];r["review_state"]="verified";r["evidence"]=[{"criterion":r["id"],"perspective":"tz","outcome":"pass","artifact_sha256":"a"*64,"receipt_ref":"r","review_ref":"r"}];self.assertTrue(gate.validate(self.d,self.o,self.c))
    def test_authority(self):self.d["actual_customer_acceptance_verified"]=True;self.assertTrue(gate.validate(self.d,self.o,self.c))
