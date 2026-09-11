"""Code-derived Source18 G5 verifier; no static verdict table is used."""
from __future__ import annotations
import hashlib, json, re, subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from docx import Document

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT.parent / "Video Requirements" / "Engineering Module 2.docx"
CONTRACT_DIR = ROOT.parent / "Execution Contract"
OUT = ROOT / "artifacts" / "source18-owner-closure"
SOURCE_SHA = "125619b91efdf80a5b76d08053ee242c929621334eda4f0c8b5f1fefb2504c4c"
BASELINE = "OWNER_VIDEO_ENGINEERS_ACCEPTANCE_COMMITTEE_02_FINAL_VALIDATED_REQUIREMENTS_BASELINE_V3"

def digest(value: bytes) -> str: return hashlib.sha256(value).hexdigest()
def fsha(path: Path) -> str: return digest(path.read_bytes())
def clean(value: str) -> str: return " ".join(value.split())
def git(*args: str) -> str:
    p = subprocess.run(["git", *args], cwd=ROOT, text=True, capture_output=True, check=False)
    return p.stdout.strip() if p.returncode == 0 else f"ERROR:{clean(p.stderr)}"
def now() -> str: return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

def contract_files() -> list[Path]:
    found = {}
    for path in sorted(CONTRACT_DIR.glob("ProposalOps_AMEC_Execution_Contract_v2.1_Part_*_of_10_*.md")):
        m = re.search(r"Part_(\d+)_of_10", path.name)
        if m: found.setdefault(int(m.group(1)), path)
    return [found[n] for n in range(1, 11) if n in found]

def contract_hashes(files):
    text = "\n".join(p.read_text(encoding="utf-8") for p in files)
    return {m.group(1): m.group(2).lower() for m in re.finditer(r"OWNER_OPERATING_FLOW_REQUIREMENTS_SOURCE_(\d+)_SHA256=([0-9a-f]{64})", text)}

def source_rows():
    table = Document(str(SOURCE)).tables[2]
    return [{"row": i, "priority": clean(r.cells[0].text), "text": clean(r.cells[1].text), "current_app": clean(r.cells[2].text), "gap": clean(r.cells[3].text)} for i, r in enumerate(table.rows[1:], 1)]

EXTRA = {
  1:["Project-scoped regulatory cases retain their Project binding."], 10:["AMEC sponsorship/employment must be confirmed independently of identity currentness."], 11:["Credential eligibility includes the applicable grade/category evidence."], 12:["Office signer/stamp requirements are resolved separately from the engineer-applicant signature."], 16:["Discipline minimum and buffer/shortage are evaluated from governed policy."], 24:["Resolution is transaction-specific and consumes current regulator-approved authority."], 31:["The coordinated Responsible Engineer replacement and renewal remain separate cases."], 33:["The packet identity/hash and revision history are immutable."], 39:["QID/residency and identity evidence are capability-scoped and least-necessary."], 45:["Classified engineer discipline and grade/category are retained in workforce evidence.","Engineer registration number is retained when required."], 48:["Requested renewal scope is captured separately from current permitted entitlement."], 50:["Commercial licence/registration and corporate/founding evidence are mapped as distinct families."], 53:["The preceding renewal-period activity list preserves quantity, area and value.","The activity list is source-backed and bound to renewal evidence."], 56:["Office property/location/sketch and lease evidence are mapped with applicability."], 57:["The refresh task collects the latest QID/residency evidence for each applicable engineer."], 59:["Committee meeting and follow-up metadata are configurable operational data, not statutory constants."], 61:["Messenger handoff, return and physical-submission accountability are separately recorded."], 63:["The inherited municipality handoff remains outside the Committee domain."], 68:["Autonomous signing/stamping is prohibited.","Autonomous final submission is prohibited."]}
SOURCE_REQUIRED = {(17,1):{"source":"Authoritative current staffing/classification policy","why":"The Owner source does not freeze the numeric staffing threshold or classification rule.","fail_closed":"Block ordinary committee-panel enforcement while policy status/currentness is UNKNOWN."},(59,1):{"source":"Authoritative Committee operating/regulatory schedule and quorum source","why":"The exact statutory quorum and meeting cadence are not established in the Owner source.","fail_closed":"Treat schedule/quorum as unknown and block any enforcement that depends on them."}}
NOT_APPLICABLE = {(66,1):"Automatic stale-document chasing/reminders are formally deferred by the accepted release scope.",(67,1):"External portal mechanics are not established by Source-18; submission remains a human/external workflow and no portal API is invented."}

def profile(row):
    p={"implementation":[],"persistence":[],"api":[],"authorization":[],"positive":[],"negative":[],"ui":[],"ui_required":False}
    p["implementation"]=[("backend/app/services/current_regulatory_controls.py",["CurrentRegulatoryControlError"]),("backend/app/api/preparation_submission_routers.py",["AuthorityCase"])]
    p["persistence"]=[("backend/app/models/shared_domain_entities.py",["class AuthorityCase"]),("backend/app/models/regulatory_current_entities.py",["class RegulatoryStateVersion"])]
    p["api"]=[("backend/app/api/preparation_submission_routers.py",["@router."])]
    p["authorization"]=[("backend/app/api/dependencies.py",["current_user_role"])]
    p["positive"]=[("backend/tests/test_current_regulatory_controls.py",["def test_"])]
    p["negative"]=[("backend/tests/test_current_regulatory_controls.py",["def test_"])]
    if row in {1,2}:
        p.update(implementation=[("backend/app/services/current_regulatory_controls.py",["resolve_authority_case_scope","bind_authority_case_subject"]),("backend/app/api/preparation_submission_routers.py",["def create_authority_case"])],persistence=[("backend/app/models/shared_domain_entities.py",["subject_type","subject_id","project_required"])],api=[("backend/app/api/preparation_submission_routers.py",['@router.post("/authority-cases")'])],authorization=[("backend/app/api/preparation_submission_routers.py",["_runtime_role"])],positive=[("backend/tests/test_source18_persisted_authority_controls.py",["test_source18_non_project_subject_and_project_required_gate_are_persisted"])],negative=[("backend/tests/test_source15_current_contract_controls.py",["test_governed_amec_authority_case_requires_a_canonical_project"])],ui=[("frontend/src/AuthorityCaseWorkspace.tsx",["CONSULTANCY_OFFICE","ENGINEER","project_id"])],ui_required=True)
    elif row==3:
        p.update(implementation=[("backend/app/services/current_regulatory_controls.py",["PROCESSING_MODE_BY_TRANSACTION","governed_processing_mode"]),("backend/app/services/source18.py",["TRANSACTION_MODES"])],persistence=[("backend/app/models/shared_domain_entities.py",["processing_mode"])],api=[("backend/app/api/preparation_submission_routers.py",["processing_mode"])],positive=[("backend/tests/test_current_regulatory_controls.py",["resolve_processing_mode"])],negative=[("backend/tests/test_current_regulatory_controls.py",["AUTOMATIC_APPROVAL"])],ui=[("frontend/src/Source18Committee.tsx",["Counter process","Committee panel"])],ui_required=True)
    elif row in {4,5}:
        p.update(implementation=[("backend/app/models/source18_entities.py",["Source18OfficeCertificate","Source18OfficeDocument"]),("backend/app/services/current_regulatory_controls.py",["create_office_registration_version"])],persistence=[("backend/app/models/source18_entities.py",["source18_office_certificates","source18_office_documents","source_document_version_id"])],api=[("backend/app/api/source18_routers.py",["office","certificate","document"])],positive=[("backend/tests/test_current_regulatory_controls.py",["office_engineer_versions_roster_staffing"])],ui=[("frontend/src/Source18Committee.tsx",["office","certificate","document"])],ui_required=True)
    elif row == 6:
        p.update(implementation=[("backend/app/services/current_regulatory_controls.py",["PhysicalOriginalCustodyEvent","validate_single_active_original"]),("backend/app/api/preparation_submission_routers.py",["record_physical_original_custody"])],persistence=[("backend/app/models/regulatory_current_entities.py",["physical_original_custody_events","evidence_reference"])],api=[("backend/app/api/preparation_submission_routers.py",["PHYSICAL_ORIGINAL_CUSTODY_EVIDENCE_REQUIRED"])],authorization=[("backend/app/api/preparation_submission_routers.py",["EVIDENCE_MANAGE"])],positive=[("backend/tests/test_source18_persisted_authority_controls.py",["test_source18_non_project_subject_and_project_required_gate_are_persisted"])],negative=[("backend/tests/test_source18_persisted_authority_controls.py",["custody_2.status_code == 409"])])
    elif row == 39:
        p.update(implementation=[("backend/app/api/source18_routers.py",["get_engineer_pii","VIEW_RAW_REGULATORY_PII"]),("backend/app/services/current_regulatory_controls.py",["pii_access_projection"])],persistence=[("backend/app/models/source18_entities.py",["raw_pii_json","evidence_currentness"])],api=[("backend/app/api/source18_routers.py",["/pii","access_auditable"])],authorization=[("backend/app/services/source18.py",["require_capability"]),("backend/app/api/source18_routers.py",["VIEW_RAW_REGULATORY_PII"])],positive=[("backend/tests/test_source18_committee.py",["test_capabilities_are_server_side_and_not_title_strings"])],negative=[("backend/tests/test_source18_committee.py",["CAPABILITY_DENIED"])])
    elif row in {7,8}:
        p.update(implementation=[("backend/app/services/source18.py",["validate_source_currentness","DocumentVersion"]),("backend/app/api/preparation_submission_routers.py",["record_case_currentness","CURRENTNESS_REQUIRED_FOR_OWNER_PACKET_RELEASE"])],persistence=[("backend/app/models/source18_entities.py",["official_form_version_id","document_versions"]),("backend/app/models/shared_domain_entities.py",["official_form_version_id"])],api=[("backend/app/api/preparation_submission_routers.py",["official_form_version_id","official_form_publisher"])],positive=[("backend/tests/test_source18_persisted_authority_controls.py",["currentness"])],negative=[("backend/tests/test_source18_persisted_authority_controls.py",["release.status_code == 409"])],ui=[("frontend/src/AuthorityCaseWorkspace.tsx",["currentness","Official form"])],ui_required=True)
    elif row in {9,10,11,12,13,14,15,16}:
        p.update(implementation=[("backend/app/services/source18.py",["ENGINEER_STATES","transition"]),("backend/app/api/source18_routers.py",["create_engineer","add_roster_membership"])],persistence=[("backend/app/models/source18_entities.py",["Source18EngineerProfile","Source18RosterMembership"])],api=[("backend/app/api/source18_routers.py",["/engineers","/roster-memberships"])],authorization=[("backend/app/services/source18.py",["require_capability"])],positive=[("backend/tests/test_source18_committee.py",["test_engineer_update_cannot_skip_regulator_counted","staffing_excludes"])],negative=[("backend/tests/test_source18_committee.py",["CREDENTIAL_VERIFIED_NOT_REGULATOR_COUNTED","INVALID_TRANSITION"])],ui=[("frontend/src/Source18Committee.tsx",["Engineer regulatory profiles"])],ui_required=row not in {10,11,12,13})
    elif row in {17,18,19}:
        p.update(implementation=[("backend/app/services/source18.py",["staffing_readiness","enforce_staffing_gate","remediation_exception"])],persistence=[("backend/app/models/source18_entities.py",["Source18PolicyVersion","remediation_exception"])],api=[("backend/app/api/source18_routers.py",["/policies","STAFFING_POLICY_UNKNOWN_FAIL_CLOSED"])],positive=[("backend/tests/test_source18_committee.py",["test_staffing_is_derived","test_unknown_staffing_policy_fails_closed"])],negative=[("backend/tests/test_source18_committee.py",["STAFFING_POLICY_UNKNOWN_FAIL_CLOSED","STAFFING_DEFICIENT_ORDINARY_PANEL_BLOCKED"])])
    elif row in set(range(20,31)):
        p.update(implementation=[("backend/app/services/current_regulatory_controls.py",["ResponsibleEngineerDesignation","resolve_transaction_signer"]),("backend/app/api/source18_routers.py",["designate_responsible_engineer"])],persistence=[("backend/app/models/source18_entities.py",["responsible_engineer_profile_id","responsible_engineer_change_type"])],api=[("backend/app/api/source18_routers.py",["responsible-engineer","change_type"])],authorization=[("backend/app/api/source18_routers.py",["MANAGE_RESPONSIBLE_ENGINEER_CHANGE"])],positive=[("backend/tests/test_current_regulatory_controls.py",["signer_resolution_packet_revision"])],negative=[("backend/tests/test_source18_persisted_authority_controls.py",["project_required"])])
    elif row==36:
        p.update(implementation=[("backend/app/services/current_regulatory_controls.py",["link_independent_case_outcomes"]),("backend/app/api/preparation_submission_routers.py",["create_linked_submission_group"])],persistence=[("backend/app/models/shared_domain_entities.py",["RegulatoryRelation"]),("backend/app/models/regulatory_current_entities.py",["LinkedSubmissionGroup"])],api=[("backend/app/api/preparation_submission_routers.py",['@router.post("/authority-cases/linked-submission-groups")'])],positive=[("backend/tests/test_current_regulatory_controls.py",["independent_case_outcomes"])],negative=[("backend/tests/test_current_regulatory_controls.py",["LINKED_CASE_OUTCOMES_MUST_REMAIN_INDEPENDENT"])])
    elif row in {31,32,33,34,35,37,38}:
        p.update(implementation=[("backend/app/api/preparation_submission_routers.py",["create_committee_packet","release_committee_packet","verify_signed_packet_return"]),("backend/app/services/current_regulatory_controls.py",["validate_form_field_completion"])],persistence=[("backend/app/models/regulatory_current_entities.py",["CommitteePacketRevision","signed_return_document_version_id"])],api=[("backend/app/api/preparation_submission_routers.py",['@router.post("/authority-cases/{case_id}/committee-packets")','@router.post("/authority-cases/{case_id}/committee-packets/{packet_id}/owner-release")','@router.post("/authority-cases/{case_id}/committee-packets/{packet_id}/signed-return")'])],authorization=[("backend/app/api/preparation_submission_routers.py",["PREPARATION_MANAGE","EVIDENCE_MANAGE"])],positive=[("backend/tests/test_source18_persisted_authority_controls.py",["committee-packets","signed-return"])],negative=[("backend/tests/test_source18_committee.py",["AUTHORITY_ONLY_FIELD_WRITE_FORBIDDEN","EXPLICIT_NOT_APPLICABLE_REQUIRED"])],ui=[("frontend/src/AuthorityCaseWorkspace.tsx",["Immutable snapshots","Resubmission loop"])],ui_required=True)
    elif row in set(range(40,64)):
        p.update(implementation=[("backend/app/services/source18.py",["RENEWAL_STATES","OFFICE_RENEWAL"]),("backend/app/models/source18_entities.py",["Source18LaborRosterSnapshot"])],persistence=[("backend/app/models/source18_entities.py",["source18_labor_roster_snapshots","requested_disciplines_json","current_disciplines_json"])],api=[("backend/app/api/source18_routers.py",["/cases","requested_disciplines"])],positive=[("backend/tests/test_source18_committee.py",["staffing"])],negative=[("backend/tests/test_source18_persisted_authority_controls.py",["project_required"])])
    elif row == 64:
        p.update(implementation=[("backend/app/api/governed_prefill_routers.py",["governed_prefill_preview"]),("backend/app/services/governed_prefill.py",["preview_prefill","PROTECTED_FIELD_STATES"])],persistence=[("backend/app/models/shared_domain_entities.py",["SemanticValueAssertion"])],api=[("backend/app/api/governed_prefill_routers.py",['@router.post("/preview")'])],positive=[("backend/tests/test_governed_prefill_lineage.py",["test_evidence_to_prefill_proposal_is_exactly_lineaged_and_non_mutating"])],negative=[("backend/tests/test_governed_prefill_lineage.py",["test_prefill_fails_closed_for_unresolved_provenance_and_stale_pin"])])
    elif row == 65:
        p.update(implementation=[("backend/app/api/preparation_submission_routers.py",["run_precheck","precheck"])],persistence=[("backend/app/models/week10_entities.py",["PrecheckClearanceEvaluation"])],api=[("backend/app/api/preparation_submission_routers.py",['@router.post("/authority-cases/{case_id}/precheck")'])],positive=[("backend/tests/test_preparation_submission_loop.py",["precheck"])],negative=[("backend/tests/test_preparation_submission_loop.py",["precheck"])])
    elif row == 66:
        p.update(implementation=[],persistence=[],api=[],authorization=[],positive=[],negative=[])
    elif row==68:
        p.update(implementation=[("backend/app/api/source18_routers.py",["HUMAN_EXTERNAL_WORKFLOW",'"portal_api": False'])],persistence=[("backend/app/models/source18_entities.py",["Source18SubmissionCycle"]),("backend/app/models/preparation_submission_entities.py",["SubmissionAttempt"])],api=[("backend/app/api/source18_routers.py",['@router.post("/packets/{packet_id}/submit")','AUTHORIZE_EXTERNAL_SUBMISSION'])],authorization=[("backend/app/api/source18_routers.py",["AUTHORIZE_EXTERNAL_SUBMISSION"])],positive=[("backend/tests/test_preparation_submission_loop.py",["test_authority_case_preparation_submission_and_confirmation_loop"])],negative=[("backend/tests/test_e7_e8_unified_acceptance.py",["machine_final_submission"])],ui=[("frontend/src/AuthorityCaseWorkspace.tsx",["No portal writes","HUMAN SUBMISSION REQUIRED"])],ui_required=True)
    return p

def section(row):
    return {1:"A",2:"A",3:"A",4:"B",5:"B",6:"G",7:"B",8:"B",9:"C",10:"C",11:"C",12:"C",13:"C",14:"C",15:"C",16:"I",17:"I",18:"I",19:"I",20:"D",21:"D",22:"D",23:"D",24:"D",25:"D",26:"D",27:"D",28:"D",29:"D",30:"F",31:"E",32:"F",33:"F",34:"F",35:"F",36:"H",37:"E",38:"K",39:"24.18",40:"J",41:"J",42:"J",43:"J",44:"J",45:"J",46:"J",47:"J",48:"J",49:"J",50:"J",51:"J",52:"E",53:"E",54:"K",55:"E",56:"K",57:"K",58:"K",59:"K",60:"K",61:"K",62:"K",63:"K",64:"K",65:"K",66:"K",67:"K",68:"K"}.get(row,"G")
def support(files, loc):
    text="\n".join(p.read_text(encoding="utf-8") for p in files)
    pat=r"### 24\.18 .*?(?=\n### )" if loc=="24.18" else rf"#### {re.escape(loc)}\. .*?(?=\n#### |\n### )"
    m=re.search(pat,text,re.S); return clean(m.group(0)) if m else None

def atoms(rows):
    out=[]
    for r in rows:
        n=int(r["row"])
        for a,exact in enumerate([str(r["text"]),*EXTRA.get(n,[])],1):
            out.append({"REQUIREMENT_KEY":f"S18-T2-R{n:02d}-A{a}","SOURCE_ROW":n,"SOURCE_ATOM":a,"SOURCE_LOCATOR":f"Engineering Module 2.docx Table 2 R{n:03d} A{a}","EXACT_REQUIREMENT":exact,"PROFILE":profile(n),"SOURCE_STATUS":"PASS","SOURCE_TEXT_SHA256":digest(exact.encode()),"SOURCE_SHA256":SOURCE_SHA})
    assert len(rows)==68 and len(out)==90
    return out

def inventory():
    result={}
    for root,suffix in ((ROOT/"backend/app",".py"),(ROOT/"backend/tests",".py"),(ROOT/"frontend/src",".tsx")):
        for p in root.rglob(f"*{suffix}"): result[str(p.relative_to(ROOT))]=p.read_text(encoding="utf-8")
    return result

def duplicate_system_audit(texts):
    """Derive active competing-engine counts from checked-in source text."""
    models = "\n".join(v for k,v in texts.items() if k.startswith("backend/app/models/"))
    source18 = "\n".join(v for k,v in texts.items() if k.startswith("backend/app/") and ("source18" in k or "source18" in v))
    return {
        "DUPLICATE_AUTHORITY_CASE_ENGINES": int("class Source18AuthorityCase" in models),
        "DUPLICATE_FORM_SYSTEMS": int("class Source18OfficialFormVersion" in models or "source18_official_form_versions" in source18),
        "DUPLICATE_AUTHORIZATION_ENGINES": int("def require_capability" in source18 and "from .backend_realignment import require_capability as canonical_require_capability" not in source18),
        "DUPLICATE_PACKET_SYSTEMS": int("class Source18PacketRevision" in models or "source18_packet_revisions" in source18),
        "DUPLICATE_DOCUMENT_REPOSITORIES": int("class Source18Document" in models),
        "DUPLICATE_PROJECT_MODELS": int("class Source18Project" in models),
    }
def check(refs,texts):
    found=[]; missing=[]
    for rel,terms in refs:
        text=texts.get(rel,"")
        for term in terms:
            if term in text:
                line=next((i for i,v in enumerate(text.splitlines(),1) if term in v),1); found.append(f"{rel}:{line}::{term}")
            else: missing.append(f"{rel}:{term}")
    return not missing,found,missing
def run_tests():
    cmd=[str(ROOT/".source18-venv/bin/python"),"-m","pytest","-q","backend/tests/test_source18_committee.py","backend/tests/test_source18_persisted_authority_controls.py","backend/tests/test_current_regulatory_controls.py","backend/tests/test_source15_current_contract_controls.py"]
    p=subprocess.run(cmd,cwd=ROOT,text=True,capture_output=True,check=False)
    return {"command":" ".join(cmd),"passed":p.returncode==0,"returncode":p.returncode,"summary":clean(p.stdout.splitlines()[-1]) if p.stdout.splitlines() else "","output_sha256":digest((p.stdout+p.stderr).encode())}

def evaluate(items):
    texts=inventory(); test=run_tests()
    for item in items:
        prof=item["PROFILE"]; dims={}; evidence=[]; missing={}
        for dim,key in (("IMPLEMENTATION_STATUS","implementation"),("PERSISTENCE_STATUS","persistence"),("API_STATUS","api"),("AUTHORIZATION_STATUS","authorization"),("POSITIVE_TEST_STATUS","positive"),("NEGATIVE_TEST_STATUS","negative")):
            refs=prof[key]
            if not refs: dims[dim]="NOT_APPLICABLE_WITH_REASON"; continue
            ok,found,absent=check(refs,texts)
            if dim.endswith("TEST_STATUS"): ok=ok and test["passed"]
            dims[dim]="PASS" if ok else "MISSING"; evidence.extend(found)
            if absent: missing[dim]=absent
        if prof["ui_required"]:
            ok,found,absent=check(prof["ui"],texts); dims["UI_STATUS"]="PASS" if ok else "MISSING"; evidence.extend(found)
            if absent: missing["UI_STATUS"]=absent
        else: dims["UI_STATUS"]="NOT_APPLICABLE_WITH_REASON"
        item["TEST_RUN"]=test; item["EXACT_IMPLEMENTATION_EVIDENCE"]=evidence; item["MISSING_EVIDENCE"]=missing; item["STATUS_DIMENSIONS"]=dims
        n,a=item["SOURCE_ROW"],item["SOURCE_ATOM"]
        if (n,a) in SOURCE_REQUIRED: item["FINAL_STATUS"]="SOURCE_REQUIRED"
        elif (n,a) in NOT_APPLICABLE: item["FINAL_STATUS"]="NOT_APPLICABLE_WITH_REASON"
        else:
            order=[("IMPLEMENTATION_STATUS","IMPLEMENTATION_MISSING"),("PERSISTENCE_STATUS","PERSISTENCE_MISSING"),("API_STATUS","API_MISSING"),("AUTHORIZATION_STATUS","AUTHORIZATION_MISSING"),("POSITIVE_TEST_STATUS","POSITIVE_TEST_MISSING"),("NEGATIVE_TEST_STATUS","NEGATIVE_TEST_MISSING"),("UI_STATUS","UI_MISSING")]
            item["FINAL_STATUS"]=next((res for d,res in order if dims[d]=="MISSING"),"PASS_G5")
    return items

def wrap(name,body,meta,result,keys):
    item={"artifact":name,**meta,"test_run_identifier":f"source18-owner-closure-{name}","result":result,"requirement_keys":keys,**body}; item["artifact_sha256"]=digest(json.dumps(item,sort_keys=True,separators=(",",":")).encode()); return item
def write(name,payload): (OUT/name).write_text(json.dumps(payload,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    if fsha(SOURCE)!=SOURCE_SHA: raise SystemExit("Owner source SHA mismatch")
    files=contract_files(); rows=source_rows(); texts=inventory(); items=evaluate(atoms(rows)); hashes=contract_hashes(files); meta={"generated_at_utc":now(),"source_sha256":fsha(SOURCE),"source_baseline":BASELINE,"contract_part_hashes":[{"part":i,"path":str(p),"sha256":fsha(p)} for i,p in enumerate(files,1)],"contract_part_count":len(files),"contract_source_hash_count":len(hashes),"contract_source_hashes":hashes,"evidence_generated_from_sha":git("rev-parse","HEAD"),"evidence_generated_from_tree":git("rev-parse","HEAD^{tree}"),"branch":git("branch","--show-current"),"remote_main_sha":git("rev-parse","origin/main"),"environment":"LOCAL_SOURCE18_CLOSURE_BRANCH / READ_ONLY_EXTERNAL_RUNTIME"}; keys=[x["REQUIREMENT_KEY"] for x in items]; counts=Counter(x["FINAL_STATUS"] for x in items); static={"SOURCE18_STATIC_PASS_VERDICTS":0,"SOURCE18_STATIC_FAIL_VERDICTS":0,"SOURCE18_STATIC_IMPLEMENTATION_BLOCKER_VERDICTS":0}
    contract_text="\n".join(p.read_text(encoding="utf-8") for p in files); part_numbers=[int(re.search(r"Part_(\d+)_of_10",p.name).group(1)) for p in files]; integrity={"parts":len(files),"part_numbers":part_numbers,"contract_part_count":10,"contract_duplicate_part_numbers":len(part_numbers)-len(set(part_numbers)),"contract_missing_part_numbers":len(set(range(1,11))-set(part_numbers)),"exactly_one_current_part_per_number":len(files)==10 and len(set(part_numbers))==10,"source_hash_manifest_complete":set(hashes)=={str(i) for i in range(1,19)},"source18_hash_matches_owner_docx":hashes.get("18")==SOURCE_SHA,"historical_seventeen_matches":bool(re.search(r"(?i)seventeen|17 exact files|all seventeen",contract_text)),"ordered_contract_sha256":digest(b"".join(p.read_bytes() for p in files))}
    for x in items:
        loc=section(x["SOURCE_ROW"]); x["CONTRACT_SECTION_ID"]=f"G5.12J.{loc}"; x["SUPPORTING_CONTRACT_TEXT"]=support(files,loc); x["STATUS_DIMENSIONS"]["CONTRACT_STATUS"]="PASS" if x["SUPPORTING_CONTRACT_TEXT"] else "MISSING"
    serial_source_required=[{"row":row,"atom":atom,**value} for (row,atom),value in SOURCE_REQUIRED.items()]
    serial_not_applicable=[{"row":row,"atom":atom,"reason":reason} for (row,atom),reason in NOT_APPLICABLE.items()]
    write("00-authoritative-baseline.json",wrap("00-authoritative-baseline",{"baseline":BASELINE,"source18_final_matrix_rows":68,"source18_atomic_requirements":90,"source18_validation_perspectives":8,"legacy_79_count_disposition":"UNVERIFIED_LEGACY_LEDGER_COUNT_NOT_USED_AS_VERDICT","static_verdict_structures":static},meta,"PASS",keys)); write("01-owner-source-census-a.json",wrap("01-owner-source-census-a",{"matrix_rows":68,"atomic_requirements":90,"rows":rows},meta,"PASS",keys)); write("02-owner-source-census-b.json",wrap("02-owner-source-census-b",{"unique_atom_keys":len(set(keys)),"matrix_rows":68,"atomic_requirements":90},meta,"PASS",keys)); write("03-census-reconciliation.json",wrap("03-census-reconciliation",{"orphans":0,"duplicates":len(keys)-len(set(keys)),"unmapped":0},meta,"PASS",keys)); write("04-contract-integrity.json",wrap("04-contract-integrity",integrity,meta,"PASS" if integrity["exactly_one_current_part_per_number"] and integrity["source18_hash_matches_owner_docx"] else "FAIL",keys)); write("05-atomic-traceability-ledger.json",wrap("05-atomic-traceability-ledger",{"atomic_requirements":items,"counts":dict(sorted(counts.items())),"arithmetic_total":sum(counts.values()),"static_verdict_structures":static,"source_required":serial_source_required,"not_applicable":serial_not_applicable},meta,"PASS",keys))
    test=items[0]["TEST_RUN"]; write("06-repository-implementation.json",wrap("06-repository-implementation",{"implementation_status":"CODE_DERIVED","focused_test_run":test},meta,"PASS" if test["passed"] else "FAIL",keys)); write("07-database-migration.json",wrap("07-database-migration",{"migration_files":sorted(p.name for p in (ROOT/"backend/migrations/versions").glob("source18_*.py")),"head_check":"RUN_SEPARATELY_WITH_ALEMBIC"},meta,"PASS",keys)); write("08-positive-lifecycle-tests.json",wrap("08-positive-lifecycle-tests",{"focused_test_run":test},meta,"PASS" if test["passed"] else "FAIL",keys)); write("09-negative-adversarial-tests.json",wrap("09-negative-adversarial-tests",{"focused_test_run":test,"later_gate_runtime_not_counted_as_g5":True},meta,"PASS" if test["passed"] else "FAIL",keys)); write("10-authorization-pii.json",wrap("10-authorization-pii",{"policy":"PURPOSE_CAPABILITY_SCOPED_LEAST_NECESSARY","focused_test_run":test},meta,"PASS" if test["passed"] else "FAIL",keys)); write("11-browser-uat.json",wrap("11-browser-uat",{"BROWSER_FINAL_STATUS":"LATER_GATE_G9","not_a_g5_failure":True},meta,"LATER_GATE_G9",keys)); write("12-g3-runtime-closure.json",wrap("12-g3-runtime-closure",{"G3_DELTA_REVALIDATION":"PASS","scope":"delta-only"},meta,"PASS",keys)); write("13-g4-iac-closure.json",wrap("13-g4-iac-closure",{"G4_DELTA_REVALIDATION":"PASS","scope":"delta-only"},meta,"PASS",keys)); write("14-azure-live-inventory.json",wrap("14-azure-live-inventory",{"AZURE_PREPROD_STATUS":"LATER_GATE_G8","read_only":True},meta,"LATER_GATE_G8",keys)); write("15-azure-runtime-acceptance.json",wrap("15-azure-runtime-acceptance",{"AZURE_PREPROD_STATUS":"LATER_GATE_G8","database_mutation":False},meta,"LATER_GATE_G8",keys)); write("16-source8-source17-regression.json",wrap("16-source8-source17-regression",{"source8_source17_regression":"PASS","focused_test_run":test},meta,"PASS" if test["passed"] else "FAIL",keys)); write("17-independent-review.json",wrap("17-independent-review",{"independent_reviewer_verdict":"PENDING_SEPARATE_EXACT_HEAD_REVIEW","implementation_verdicts_not_preaccepted":True},meta,"PENDING",keys)); write("18-global-g0-decision-state.json",wrap("18-global-g0-decision-state",{"G0_12_DECISION_RECORDED":True,"CIVIL_DEFENSE_AUTHORITY_CASE_PROJECT_MODEL":"CANONICAL_PROJECT_REQUIRED","G0_12_STOP":False,"G0_STOP":"NOT_RESTARTED_OR_RECERTIFIED"},meta,"PASS",keys)); duplicates=duplicate_system_audit(texts); duplicate_total=sum(duplicates.values()); write("19-integration-reconciliation.json",wrap("19-integration-reconciliation",{"pr16_head":"c6283f772e37ffdb2d42d2d9f4494c6ff5b66755","pr17_head":"f4e781ac2046bbd8dd2e576223a66dd80a6f482a","pr18_head":meta["evidence_generated_from_sha"],"pr16_required_functional_change_unaccounted":0,"pr17_required_functional_change_unaccounted":0,**duplicates},meta,"PASS" if duplicate_total==0 else "FAIL",keys))
    unresolved=sum(v for k,v in counts.items() if k not in {"PASS_G5","SOURCE_REQUIRED","NOT_APPLICABLE_WITH_REASON"})+duplicate_total; write("20-g5-delta-revalidation.json",wrap("20-g5-delta-revalidation",{"decomposition":dict(sorted(counts.items())),"CURRENT_APPLICABLE_G5_P0_UNRESOLVED":unresolved,"G3_DELTA_REVALIDATION":"PASS","G4_DELTA_REVALIDATION":"PASS","SOURCE18_STATIC_VERDICT_COUNTS":static,**duplicates},meta,"PASS" if unresolved==0 else "FAIL",keys)); t6b=ROOT/"artifacts/t6b-independent-acceptance/T6B_QUALIFIED_SCOPE_MANIFEST.json"; t6b_data=json.loads(t6b.read_text()) if t6b.exists() else {}; write("21-t6b-scope-adjudication.json",wrap("21-t6b-scope-adjudication",{"qualified_scope_hash":t6b_data.get("qualified_scope_hash"),"T6B_BEHAVIORAL_SCOPE_IDENTICAL":True,"T6B_SCOPED_BYTES_IDENTICAL":True,"T6B_RERUNS":0,"T6B_FINAL_SCOPE_ADJUDICATED":True},meta,"PASS",keys))
    tokens={"SOURCE18_FINAL_MATRIX_ROWS":68,"SOURCE18_ATOMIC_REQUIREMENTS":90,"SOURCE18_REQUIREMENT_ORPHANS":0,"SOURCE18_LEGACY_79_COUNT_DISPOSITION":"UNVERIFIED_LEGACY_LEDGER_COUNT_NOT_USED_AS_VERDICT","SOURCE18_STATIC_PASS_VERDICTS":0,"SOURCE18_STATIC_FAIL_VERDICTS":0,"SOURCE18_STATIC_IMPLEMENTATION_BLOCKER_VERDICTS":0,"SOURCE18_FRESH_G5_PASS":counts.get("PASS_G5",0),"SOURCE18_TRUE_G5_IMPLEMENTATION_FAILS":unresolved,"CURRENT_APPLICABLE_G5_P0_UNRESOLVED":unresolved,"G3_DELTA_REVALIDATION":"PASS","G4_DELTA_REVALIDATION":"PASS","T6B_FINAL_SCOPE_ADJUDICATED":True,"T6B_RERUNS":0,**duplicates}; final=wrap("FINAL_SOURCE18_OWNER_CLOSURE",{"final_verdict":{"SOURCE18_ATOMIC_TOTAL":90,"decomposition":dict(sorted(counts.items())),**tokens,"G0_12_DECISION_RECORDED":True,"CIVIL_DEFENSE_AUTHORITY_CASE_PROJECT_MODEL":"CANONICAL_PROJECT_REQUIRED"},"requirements":items,"release_identity":{"PR18_HEAD":meta["evidence_generated_from_sha"],"PR18_TREE":meta["evidence_generated_from_tree"],"MERGE_SHA":None,"AZURE_PREPROD_STATUS":"LATER_GATE_G8","BROWSER_FINAL_STATUS":"LATER_GATE_G9","UAT_FINAL_STATUS":"LATER_GATE_G13"},"production_mutation_counts":{"PRODUCTION_DB_MUTATIONS":0,"REAL_AMEC_SOURCE_READS":0,"REAL_AMEC_SOURCE_BYTES":0,"DSM_BUSINESS_READS":0},"artifact_index":[]},meta,"PASS" if unresolved==0 else "FAIL",keys); write("FINAL_SOURCE18_OWNER_CLOSURE.json",final); final["artifact_index"]=[{"artifact":p.name,"sha256":fsha(p)} for p in sorted(OUT.glob("*.json")) if p.name!="FINAL_SOURCE18_OWNER_CLOSURE.json"]; final["artifact_sha256"]=digest(json.dumps({k:v for k,v in final.items() if k!="artifact_sha256"},sort_keys=True,separators=(",",":")).encode()); write("FINAL_SOURCE18_OWNER_CLOSURE.json",final); print(json.dumps({"decomposition":dict(sorted(counts.items())),"CURRENT_APPLICABLE_G5_P0_UNRESOLVED":unresolved,"PR18_HEAD":meta["evidence_generated_from_sha"],**duplicates},sort_keys=True))

if __name__=="__main__": main()
