"""Structural candidate acceptance gate. No claim of actual customer acceptance."""
import csv,hashlib,io,json,re,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
PIN="e1504385d6227c44611027dc0547bcd8f0e6105e"
PATHS={
"docs/tz-audit/requirements.psv":"40a97f7406d566ea3622f07a4efc25e16bbfc58dbbc391085e4f8b8e1fc19b81",
"specs/001-contract-tz-traceability/acceptance.md":"47afe8310ff3c6e0dea56e080bb6db3a6eae12e22f8aebd044e15a824fb9693e",
"specs/001-contract-tz-traceability/spec.md":"e58f01cab7089b2408d8fef34d820de36bba0c76131faa7f33812ba740015c81",
"specs/002-signed-contract/contract-clause-checklist.md":"0333aeb49d297c048d9162e84beb272aa893265e311c86135568e2e668c29646",
"docs/tz-audit/CONTRACT_CLAUSE_MAP.csv":"5cd1f6c74c322e32cb5148dcf96126118819cfa2c7fdb650f9d654beba91f5a6"}
def validate(data,original,current):
    errors=[]
    for p,h in PATHS.items():
        if hashlib.sha256(original[p]).hexdigest()!=h:errors.append("baseline hash "+p)
        if current[p]!=original[p]:errors.append("unreviewed source drift "+p)
    if data.get("schema")!="arvectum.musbread.acceptance-review/1" or data.get("source_commit")!=PIN or data.get("actual_customer_acceptance_verified") is not False or data.get("execution_authorized") is not False:errors.append("scope/authority")
    docs=[original[p].decode("utf-8-sig") for p in PATHS]
    reg=list(csv.DictReader(io.StringIO(docs[0]),delimiter="^"))
    expected={r["ID"]:r["Фактически готово"] for r in reg}
    ids={f"TZ-{n:03d}" for n in range(1,326)}
    if len(reg)!=325 or set(expected)!=ids:errors.append("native TZ coverage")
    a=re.findall(r"^\|\s*(TZ-\d{3})\s*\|",docs[1],re.M)
    s=set(re.findall(r"\bTZ-\d{3}\b",docs[2]))
    if len(a)!=325 or set(a)!=ids or s!=ids:errors.append("acceptance/spec coverage")
    numbered=re.findall(r"^\|\s*(\d+(?:\.\d+)+)\s*\|",docs[3],re.M)
    cross=[r["Пункт договора"] for r in csv.DictReader(io.StringIO(docs[4]),delimiter=";")]
    if len(numbered)!=124 or len(set(numbered))!=124 or len(cross)!=125 or len(set(cross))!=125 or set(cross)-set(numbered)!={"10"} or set(numbered)-set(cross):errors.append("contract section coverage")
    for kind,keys in [("tz",ids),("clauses",set(cross))]:
        rows=data.get(kind,[]);actual=[r["id"] for r in rows]
        if len(actual)!=len(set(actual)) or set(actual)!=keys:errors.append(kind+" review coverage")
        for r in rows:
            k=r["id"]
            if kind=="tz" and (r.get("native_task_ref")!=k or r.get("source_status")!=expected.get(k)):errors.append("native status/ref drift "+k)
            if kind=="clauses" and r.get("source")!=("section_level_crosswalk" if k=="10" else "numbered_checklist"):errors.append("clause type "+k)
            if r.get("review_state") not in {"unverified","verified"}:errors.append("review state "+k)
            if r.get("review_state")=="verified":
                ev=r.get("evidence",[])
                if not ev or any(e.get("criterion")!=k or e.get("perspective")!=kind or e.get("outcome")!="pass" or not re.fullmatch(r"[0-9a-f]{64}",e.get("artifact_sha256","")) or not e.get("receipt_ref") or not e.get("review_ref") for e in ev):errors.append("missing criterion-specific reviewed evidence "+k)
    return errors
def inputs():
    original={p:subprocess.check_output(["git","-C",str(ROOT),"show",PIN+":"+p]) for p in PATHS}
    current={p:(ROOT/p).read_bytes() for p in PATHS}
    return json.loads((ROOT/"specs/002-signed-contract/acceptance-review.json").read_text()),original,current
if __name__=="__main__":
    errors=validate(*inputs())
    if errors:raise SystemExit("\n".join(errors))
    print("Structural PASS: 325 TZ records; 124 numbered clauses plus section 10. Actual acceptance not established.")
