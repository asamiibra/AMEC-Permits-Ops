"""Weeks 1–8 reconciliation invariants."""

from backend.app.fixtures.canonical import CANONICAL_APPLICATION_IDS, CANONICAL_PROJECT_IDS
from backend.app.services.configuration_lineage import stable_hash
from pathlib import Path
import re


def test_single_canonical_fixture_authority_and_identity_links(client):
    fixture = client.get("/api/reconciliation/fixture").json()
    assert fixture["fixture_set_id"] == "PermitOps_Synthetic_MVP_Dataset_v1"
    assert fixture["fixture_version"] == "1.1.1"
    assert len(fixture["manifest_sha256"]) == 64
    assert fixture["active_golden_path_authorities"] == 1
    assert fixture["manifest"]["projects"] == CANONICAL_PROJECT_IDS
    assert fixture["manifest"]["applications"] == CANONICAL_APPLICATION_IDS
    projects = {item["project_number"]: item for item in client.get("/api/projects").json()}
    applications = {item["external_request_number"]: item for item in client.get("/api/applications").json()}
    assert set(CANONICAL_PROJECT_IDS).issubset(projects)
    assert set(CANONICAL_APPLICATION_IDS).issubset(applications)
    assert all(applications[number]["project_id"] == projects[CANONICAL_PROJECT_IDS[index]]["id"] for index, number in enumerate(CANONICAL_APPLICATION_IDS))
    first = client.get(f"/api/reconciliation/properties/{projects[CANONICAL_PROJECT_IDS[0]]['id']}").json()
    assert len(first["owners"]) == 2
    assert first["owners"][0]["normalized_share"] + first["owners"][1]["normalized_share"] == 1.0


def test_governance_does_not_promote_synthetic_evidence(client):
    body = client.get("/api/reconciliation/governance").json()
    tracks = {item["track"]: item["status"] for item in body["tracks"]}
    assert tracks == {"TRACK_A": "ACTIVE_SYNTHETIC", "TRACK_B": "NOT_AUTHORIZED", "TRACK_C": "NOT_AUTHORIZED"}
    assert body["real_data_approval"] is False
    assert body["production_g10"] is False
    assert "NOT CLIENT-APPROVED BUILD" in body["labels"]


def test_stage2_review_acknowledgement_is_not_approval(client):
    baseline = client.post("/api/stage2/baseline/generate", json={}).json()
    acknowledged = client.post(f"/api/stage2/baseline/{baseline['id']}/acknowledgements", json={"reviewer_name": "synthetic-reviewer", "reviewer_role": "REQUIREMENT_STEWARD", "acknowledgement": "REVIEWED"})
    assert acknowledged.status_code == 200
    body = acknowledged.json()
    assert body["baseline_version"] == baseline["version"]
    assert body["baseline_checksum"] == baseline["checksum"]
    assert body["baseline_status"] == "DRAFT"
    assert body["reviewed_is_not_approved"] is True


def test_configuration_bundle_is_stable_and_reconstructable(client):
    first = client.get("/api/reconciliation/configuration-bundle").json()
    second = client.get("/api/reconciliation/configuration-bundle").json()
    assert first["bundle"]["bundle_id"] == second["bundle"]["bundle_id"]
    assert first["bundle"]["checksum"] == second["bundle"]["checksum"]
    assert {item["artifact_type"] for item in first["artifacts"]} >= {"REQUIREMENT_CONFIGURATION", "FIELD_AUTHORITY_RULE_SET", "TARGET_RENDERING_RULE_SET", "ATTACHMENT_TAXONOMY", "FINDING_CODE_TAXONOMY"}


def test_safety_contract_has_no_machine_final_submit(client):
    openapi = client.get("/openapi.json").json()
    paths = " ".join(openapi["paths"].keys()).upper()
    permit_paths = " ".join(path for path in openapi["paths"].keys() if not path.startswith("/api/billing")).upper()
    operations = str(openapi).upper()
    assert "FINAL_SUBMIT" not in paths
    assert "SUBMIT_APPLICATION" not in operations
    # Billing has an explicitly bounded payment-evidence/allocation seam; the
    # permit workflow safety contract remains unchanged outside that namespace.
    assert "PAYMENT" not in permit_paths
    assert "SIGNATURE" not in paths


def test_authoritative_registry_has_exact_a12_numbers_and_titles():
    registry = Path("config/recording_fidelity_requirements_v2_5.yaml").read_text(encoding="utf-8")
    rows = re.findall(r'^  - number: (\d+)\n    canonical_title: "([^"]+)"', registry, re.MULTILINE)
    expected_titles = [
        "Project-start trigger → project number → standard Synology project/template creation",
        "One canonical synthetic fixture universe",
        "Synology ↔ PermitOps ↔ Excel operating loop",
        "Recording-derived Excel structure",
        "Multi-owner/property/representation semantics",
        "Forms and undertakings generated from verified facts",
        "Target rendering rules",
        "Minimum package definition + readiness + locked manifest",
        "Internal human review gates",
        "Assisted municipality operator surface",
        "Complete synthetic portal-preparation chain",
        "Human submission handoff + authority-state confirmation",
        "Status/repetition/comment monitoring",
        "Finding lifecycle and resubmission gate",
        "Notification delivery",
        "Historical finding reuse / recurrence prevention",
        "Authority AI/precheck correction loop",
        "Attended authentication and role handoff",
        "Complete attachment behavior",
        "One canonical end-to-end golden path",
    ]
    assert [int(number) for number, _ in rows] == list(range(1, 21))
    assert [title for _, title in rows] == expected_titles


def test_configuration_checksum_changes_only_with_semantic_change():
    semantic = {"field": "PROPERTY.PLOT_NUMBER", "version": "1.0"}
    assert stable_hash(semantic) == stable_hash({"version": "1.0", "field": "PROPERTY.PLOT_NUMBER"})
    assert stable_hash(semantic) != stable_hash({"field": "PROPERTY.PLOT_NUMBER", "version": "2.0"})
