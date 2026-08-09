from backend.app.api.week3_routers import recommend_phase0


def test_phase0_recommendation_rules_are_transparent():
    common = dict(approved_data=True, pilot_available=True, bounded_scenario=True, assisted_viable=True, tier1_blocker=False, automation_available=False, candidate_agreement=0.99, keyed_fallback=True)
    assert recommend_phase0(**{**common, "approved_data":False}) .value == "PAUSE"
    assert recommend_phase0(**common).value == "GO_WITH_FALLBACK"
    assert recommend_phase0(**{**common, "candidate_agreement":0.50}).value == "GO_WITH_REDUCED_DEPTH"
    assert recommend_phase0(**{**common, "assisted_viable":False}).value == "NO_GO"


def test_adjudication_workflow_and_role_boundary(client):
    cases = client.get("/api/evaluation/adjudications").json()
    assert len(cases) == 15
    disputed = next(c for c in cases if c["status"] == "DISPUTED")
    denied = client.post(f"/api/evaluation/adjudications/{disputed['id']}/resolve", json={"action":"CONFIRM_GROUND_TRUTH","actor_id":"random-user"})
    assert denied.status_code == 403
    corrected = client.post(f"/api/evaluation/adjudications/{disputed['id']}/resolve", json={"action":"CORRECT_GROUND_TRUTH","actor_id":"synthetic-steward","expected_class":"DRAWING_SET"})
    assert corrected.status_code == 200 and corrected.json()["status"] == "ADJUDICATED"
    history = client.get(f"/api/evaluation/adjudications/{disputed['id']}").json()["history"]
    assert any(h["action"] == "CORRECT_GROUND_TRUTH" for h in history)


def test_week3_analysis_separates_automation_and_control_quality(client):
    profile = client.get("/api/evaluation/analysis").json()["profile"]
    assert profile["classification"]["documents_evaluated"] == 15
    assert profile["candidate_extraction"]["candidate_correct"] == 67
    assert profile["final_control_quality"]["final_verified_agreement"] == 1.0
    assert profile["final_control_quality"]["critical_false_accepts"] == 0


def test_synthetic_thresholds_remain_non_contractual(client):
    thresholds = client.get("/api/stage2/thresholds").json()["thresholds"]
    item = next(x for x in thresholds if x["metric_code"] == "FINAL_CRITICAL_FIELD_AGREEMENT")
    assert item["sample_size"] == 85 and item["status"] == "PROPOSED"
    denied = client.patch(f"/api/stage2/thresholds/{item['id']}", json={"status":"APPROVED_STAGE_2"})
    assert denied.status_code == 403


def test_corpus_tier1_and_tier2_governance(client):
    corpus = client.get("/api/stage2/acceptance-corpus").json()
    assert corpus["minimum_cases"] == 25 and corpus["coverage"]["missing"]
    decisions = client.get("/api/stage2/tier1-decisions").json()
    assert any(x["status"] == "OPEN" for x in decisions)
    backlog = client.get("/api/stage2/tier2-backlog").json()
    assert any(x["blocking_week6"] for x in backlog)
    created = client.post("/api/stage2/tier2-backlog", json={"category":"EDGE_CASE","title":"New municipality automation","description":"New municipality scope","owner":"Synthetic Lead","due_build_week":4})
    assert created.status_code == 200 and created.json()["scenario_expansion_warning"] is True


def test_delivery_municipality_pilot_and_precheck(client):
    scenarios = client.get("/api/stage2/delivery-scenarios").json()
    selected = next(x for x in scenarios if x["scenario_code"] == "QATAR_LOCAL_ACCESS_HEAVY")
    assert client.patch(f"/api/stage2/delivery-scenarios/{selected['id']}", json={"status":"SELECTED_DEMO"}).status_code == 200
    operations = client.get("/api/stage2/municipality-operations").json()
    assert len(operations) == 9 and "SUBMIT_APPLICATION" not in {x["operation"] for x in operations}
    assert client.get("/api/stage2/precheck-decision").json()["available"] is True
    assert client.get("/api/stage2/pilot-cohort").json()["preparers"]


def test_phase0_recommendation_requires_human_record(client):
    close = client.get("/api/phase0/close").json()
    assert close["system_recommendation"] == "PAUSE"
    assert client.get("/api/phase0/status").json()["recommendation"] is None
    recorded = client.post("/api/phase0/decision", json={"decision":"GO_WITH_FALLBACK","summary":"Synthetic demo decision","conditions":close["conditions"],"blockers":close["blockers"],"fallbacks":["ASSISTED"],"evidence_refs":["synthetic://analysis"],"approved_by":"Synthetic Demo Approver"})
    assert recorded.status_code == 200 and recorded.json()["status"] == "AUTHORIZED_DEMO"


def test_stage2_baseline_is_checksumed_and_immutable_after_approval(client):
    generated = client.post("/api/stage2/baseline/generate", json={})
    assert generated.status_code == 200
    baseline = generated.json()
    assert len(baseline["checksum"]) == 64 and baseline["status"] == "DRAFT"
    assert client.post(f"/api/stage2/baseline/{baseline['id']}/approve", json={"status":"APPROVED_WITH_CONDITIONS"}).status_code == 200
    assert client.post(f"/api/stage2/baseline/{baseline['id']}/approve", json={"status":"APPROVED"}).status_code == 409
    new_version = client.post("/api/stage2/baseline/generate", json={}).json()
    assert new_version["version"] != baseline["version"]


def test_signoff_c_payment_plan_and_safety_export(client):
    client.post("/api/stage2/baseline/generate", json={})
    proposal = client.post("/api/commercial/signoff-c/generate", json={})
    assert proposal.status_code == 200
    body = proposal.json()
    assert body["status"] == "DRAFT" and body["holdback_percent"] == 5 and body["hypercare_weeks"] == 4
    assert sum(x["percent"] for x in body["payment_plan_json"]) == 100
    export = client.get("/api/phase0/handoff-export").json()
    assert export["synthetic_only"] is True and export["secrets_included"] is False and export["raw_documents_included"] is False
