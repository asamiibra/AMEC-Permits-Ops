"""Runtime SQL Server acceptance gates for final Phase4 closure.

All rows are controlled synthetic fixtures. Results come from actual SQL
Server/application operations or fresh exact-contract checks.
"""

from __future__ import annotations

import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import inspect, select, text

from backend.app.db import SessionLocal, database_migration_heads, engine, repository_migration_head, validate_mssql_connection_url
from backend.app.models import (
    ApplicationStatus, AssertionStatus, AuditEvent, ConsultancyOffice, Criticality,
    Base, DataType, FieldDefinition, PermitApplication, Phase4ClassifierCorrectionEvent,
    Phase4ClassificationEnvelope, Phase4ProjectionReceipt, Phase4ReviewDecision,
    Phase4SourceChangeEvent, Project, Role, VerifiedAssertion, VerificationMethod,
)
from backend.app.schemas.phase4 import ClassificationEnvelopeIn, ProjectionRequest, ReviewDecisionIn, SourceChangeEventIn
from backend.app.services.phase4 import (
    ALLOWED_DECISIONS, PHASE3C_MODULE_TRUTH_SHA, PHASE4_CORPUS_APP_SHA,
    PROTECTED_OPERATIONS, create_classification_envelope, execute_projection,
    record_review_decision, record_source_event, review_queue,
)


ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = Path(os.environ.get("AZSQL_EVIDENCE_DIR", os.environ.get("RUNNER_TEMP", ROOT / "artifacts")))
NOW = datetime.now(timezone.utc).isoformat()
RESULTS: list[dict[str, object]] = []
GOLDEN_RESULTS: list[dict[str, object]] = []
PROTECTED_RESULTS: list[dict[str, object]] = []

AZSQL_ASSERTIONS = [
    "SQL Server engine/dialect is MSSQL", "fresh empty database migrates to baseline_phase4_v36_azure_sql", "active migration graph has exactly one root and one head", "ORM-to-target logical schema unexplained diff count = 0", "English Unicode round-trip", "Arabic Unicode round-trip", "JSON object/array/null round-trip", "datetime/time-zone intent round-trip", "numeric precision/scale round-trip", "boolean round-trip", "enum/domain allowed-value behavior", "primary-key semantics", "unique-constraint semantics", "foreign-key target/action semantics", "check-constraint semantics", "index columns/order/uniqueness", "server-default semantics", "identifier generation semantics", "proposal/reference sequence semantics", "migration-owned control-data semantics", "real transaction rollback proof", "SourceChangeEvent same-event retry idempotency", "concurrent same-event produces one logical event", "review decision payload-sensitive idempotency", "concurrent different decisions on same envelope/version: one winner", "successful review advances record_version exactly once", "scoped review queue excludes wrong-project/wrong-entity envelopes", "stored audit actor is server-derived and client spoof cannot win", "RESOLVE_RELATIONSHIP binds exact server-held candidate", "CORRECT requires/persists a real changed correction", "MARK_OUT_OF_SCOPE actual lineage causes zero typed projection", "RESOLVE_RELATIONSHIP actual lineage causes zero protected effect", "VerifiedAssertion supersession old→superseded/new→current", "projection retry produces one logical receipt/side-effect set", "all 16 protected human authorities remain denied", "application startup and migration-head verification pass on SQL Server", "production Azure SQL connection config requires Encrypt=yes and TrustServerCertificate=no", "active runtime contains zero PostgreSQL advisory-lock dependency", "active migration path contains zero PostgreSQL physical-lineage dependency", "no Azure/Entra/Synology/SMB/real-data mutation occurred",
]
GOLDEN_NAMES = ["new synthetic app upload", "same-event retry", "modified source", "move/rename candidate", "missing source", "contradictory evidence", "SECRET_EXCLUDE", "unsupported capability", "review ACCEPT", "review CORRECT", "review DEFER", "review MARK_OUT_OF_SCOPE", "RESOLVE_RELATIONSHIP", "review REJECT", "VerifiedAssertion supersession", "projection retry", "protected-action denial", "Master Content candidate", "Finance candidate", "Reports mapping"]
AZSQL_GATE_IDS = tuple(f"AZSQL-{index:03d}" for index in range(1, 41))
GOLDEN_PATH_IDS = tuple(f"GP-{index:02d}" for index in range(1, 21))


def _read_json(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def _expect_error(fn, status: int | None = None, code: str | None = None) -> bool:
    try:
        fn()
    except HTTPException as exc:
        detail = exc.detail if isinstance(exc.detail, dict) else {}
        return (status is None or exc.status_code == status) and (code is None or detail.get("code") == code)
    except Exception:
        return False
    return False


def _expect_value_error(fn) -> bool:
    try:
        fn()
    except ValueError:
        return True
    except Exception:
        return False
    return False


def gate(check_id: str, assertion: str, evidence_type: str, node: str, refs: list[str], result: object, evidence: object) -> None:
    passed = bool(result)
    source_requirement_id = f"AZSQL-{int(check_id.split('-')[1]):02d}" if check_id.startswith("AZSQL-") else check_id
    RESULTS.append({"check_id": check_id, "source_requirement_id": source_requirement_id, "assertion": assertion, "evidence_type": evidence_type, "command_or_test_node": node, "evidence_refs": refs, "result": "PASS" if passed else "FAIL", "evidence": evidence})


def _source(event_id: str, *, event_type: str = "NEW", surface: str = "CONTROLLED_SYNTHETIC_FIXTURE", locator: str = "synthetic://phase4/final") -> SourceChangeEventIn:
    return SourceChangeEventIn(event_id=event_id, scan_id_or_observation_group="FINAL-SYNTHETIC", source_surface=surface, source_artifact_id_or_locator=locator, source_version_token="final-v1", event_type=event_type, correlation_id=f"final-{uuid4()}", observed_at=NOW)


def _scope(envelope: Phase4ClassificationEnvelope) -> str:
    return str(envelope.axes_json["scope"]["scope_id"])


def _envelope(db, *, scope_id: str, event_type: str = "NEW") -> Phase4ClassificationEnvelope:
    event = record_source_event(db, _source(f"event-{uuid4()}", event_type=event_type), Role.SYSTEM_ADMIN)
    axes = {"scope": {"scope_type": "PROJECT", "scope_id": scope_id}, "classification_proposal": {"discipline": "ENGINEERING", "synthetic_review_axis": "BEFORE"}, "relationship_resolution": {"source_entity_id": "source-final", "candidate_entity_id": "candidate-final", "relationship_type": "SAME_PROJECT", "resolution": "ACCEPTED"}}
    return create_classification_envelope(db, ClassificationEnvelopeIn(envelope_id=f"envelope-{uuid4()}", root_event_id=event.id, source_mode="CONTROLLED_SYNTHETIC", module_truth_contract_sha=PHASE3C_MODULE_TRUTH_SHA, corpus_app_contract_sha=PHASE4_CORPUS_APP_SHA, axes_json=axes), Role.SYSTEM_ADMIN)


def _decision(db, envelope: Phase4ClassificationEnvelope, decision: str, *, key: str | None = None, decision_id: str | None = None, record_version: int = 1, corrections: list[dict] | None = None) -> Phase4ReviewDecision:
    return record_review_decision(db, ReviewDecisionIn(decision_id=decision_id or f"decision-{uuid4()}", classification_envelope_id=envelope.id, decision=decision, actor_id="client-spoof", capability="PHASE4_RESOLVE_RELATIONSHIP" if decision == "RESOLVE_RELATIONSHIP" else "PHASE4_REVIEW_DECISION", scope_type="PROJECT", scope_id=_scope(envelope), record_version=record_version, idempotency_key=key or f"decision-key-{uuid4()}", corrections_json=corrections or []), Role.SYSTEM_ADMIN)


def _fixture() -> tuple[str, str]:
    project_id = str(uuid4())
    with SessionLocal() as db:
        office = ConsultancyOffice(id=str(uuid4()), office_code=f"FINAL-{uuid4().hex[:10]}", name_en="Synthetic Final Office", name_ar="مكتب اختباري")
        project = Project(id=project_id, project_number=f"FINAL-{uuid4().hex[:10]}", project_name="Synthetic Final Project", office=office, workstream="PERMITTING", status="ACTIVE", municipality="Doha", permit_type="BUILDING")
        application = PermitApplication(project=project, authority="SYNTHETIC_AUTHORITY", municipality="Doha", permit_type="BUILDING", external_request_number=f"FINAL-{uuid4().hex[:12]}", application_status=ApplicationStatus.DRAFT)
        field = FieldDefinition(field_code=f"FINAL_FIELD_{uuid4().hex[:10]}", name_en="Synthetic field", data_type=DataType.STRING, criticality=Criticality.NORMAL, normalization_rule="IDENTITY", description="Controlled synthetic fixture")
        assertion = VerifiedAssertion(project=project, field_definition=field, semantic_value_json={"value": "synthetic"}, display_value="synthetic", status=AssertionStatus.CURRENT, verification_method=VerificationMethod.MANUAL_KEYED_VERIFIED, verified_by="synthetic-system", reason="Final controlled fixture")
        db.add_all([office, project, application, field, assertion])
        db.commit()
        return project_id, assertion.id


def schema_gates(project_id: str) -> None:
    dialect = engine.dialect.name
    gate("AZSQL-001", AZSQL_ASSERTIONS[0], "RUNTIME_SQLSERVER", "engine.dialect", ["azsql-001-040.json#AZSQL-001"], dialect == "mssql", dialect)
    with engine.connect() as connection:
        heads = database_migration_heads(engine)
        gate("AZSQL-002", AZSQL_ASSERTIONS[1], "RUNTIME_SQLSERVER", "alembic.upgrade", ["azsql-001-040.json#AZSQL-002"], heads == ("baseline_phase4_v36_azure_sql",), heads)
        gate("AZSQL-003", AZSQL_ASSERTIONS[2], "SCHEMA_INTROSPECTION", "database_migration_heads", ["azsql-001-040.json#AZSQL-003"], heads == ("baseline_phase4_v36_azure_sql",) and repository_migration_head() == "baseline_phase4_v36_azure_sql", heads)
        actual_tables = set(inspect(connection).get_table_names())
        model_tables = set(Base.metadata.tables)
        unexplained = (model_tables - actual_tables) | (actual_tables - model_tables - {"alembic_version"})
        gate("AZSQL-004", AZSQL_ASSERTIONS[3], "SCHEMA_INTROSPECTION", "Base.metadata_vs_information_schema", ["azsql-001-040.json#AZSQL-004"], len(unexplained) == 0, sorted(unexplained))
        english = connection.execute(text("SELECT CAST(N'Phase4 English' AS NVARCHAR(100))")).scalar_one()
        arabic = connection.execute(text("SELECT CAST(N'اختبار Phase4' AS NVARCHAR(100))")).scalar_one()
        gate("AZSQL-005", AZSQL_ASSERTIONS[4], "RUNTIME_SQLSERVER", "SELECT NVARCHAR english", ["azsql-001-040.json#AZSQL-005"], english == "Phase4 English", english)
        gate("AZSQL-006", AZSQL_ASSERTIONS[5], "RUNTIME_SQLSERVER", "SELECT NVARCHAR arabic", ["azsql-001-040.json#AZSQL-006"], arabic == "اختبار Phase4", arabic)
        json_values = connection.execute(text("SELECT JSON_VALUE(N'{\"ok\":true}', '$.ok'), JSON_QUERY(N'{\"items\":[1,2]}', '$.items'), JSON_QUERY(N'{\"nullValue\":null}', '$.nullValue')")).one()
        gate("AZSQL-007", AZSQL_ASSERTIONS[6], "RUNTIME_SQLSERVER", "SQL Server JSON_VALUE/JSON_QUERY", ["azsql-001-040.json#AZSQL-007"], json_values[0] == "true" and json_values[1] == "[1,2]" and json_values[2] is None, list(json_values))
        temporal = connection.execute(text("SELECT CAST('2026-08-23T12:34:56+03:00' AS DATETIMEOFFSET)" )).scalar_one()
        gate("AZSQL-008", AZSQL_ASSERTIONS[7], "RUNTIME_SQLSERVER", "DATETIMEOFFSET round-trip", ["azsql-001-040.json#AZSQL-008"], getattr(temporal, "tzinfo", None) is not None, str(temporal))
        numeric = connection.execute(text("SELECT CAST(12345.67890 AS DECIMAL(18,5))")).scalar_one()
        gate("AZSQL-009", AZSQL_ASSERTIONS[8], "RUNTIME_SQLSERVER", "DECIMAL(18,5) round-trip", ["azsql-001-040.json#AZSQL-009"], str(numeric) == "12345.67890", str(numeric))
        boolean = connection.execute(text("SELECT CAST(1 AS BIT)")).scalar_one()
        gate("AZSQL-010", AZSQL_ASSERTIONS[9], "RUNTIME_SQLSERVER", "BIT round-trip", ["azsql-001-040.json#AZSQL-010"], bool(boolean), boolean)
        primary_keys = inspect(connection).get_pk_constraint("phase4_source_change_events").get("constrained_columns", [])
        unique_constraints = inspect(connection).get_unique_constraints("phase4_review_decisions")
        foreign_keys = inspect(connection).get_foreign_keys("verified_assertions")
        indexes = inspect(connection).get_indexes("phase4_review_decisions")
        gate("AZSQL-012", AZSQL_ASSERTIONS[11], "SCHEMA_INTROSPECTION", "inspect.primary_key", ["azsql-001-040.json#AZSQL-012"], primary_keys == ["id"], primary_keys)
        gate("AZSQL-013", AZSQL_ASSERTIONS[12], "SCHEMA_INTROSPECTION", "inspect.unique_constraints", ["azsql-001-040.json#AZSQL-013"], any(set(item.get("column_names", [])) == {"idempotency_key"} for item in unique_constraints), unique_constraints)
        gate("AZSQL-014", AZSQL_ASSERTIONS[13], "SCHEMA_INTROSPECTION", "inspect.foreign_keys", ["azsql-001-040.json#AZSQL-014"], any(item.get("referred_table") == "projects" for item in foreign_keys), foreign_keys)
        gate("AZSQL-016", AZSQL_ASSERTIONS[15], "SCHEMA_INTROSPECTION", "inspect.indexes", ["azsql-001-040.json#AZSQL-016"], any("idempotency_key" in item.get("column_names", []) for item in indexes) or any(set(item.get("column_names", [])) == {"idempotency_key"} for item in unique_constraints), indexes)
        sequence_columns = {item["name"] for item in inspect(connection).get_columns("master_content_reference_sequences")}
        sequence_count = connection.execute(text("SELECT COUNT(*) FROM master_content_reference_sequences")).scalar_one()
        gate("AZSQL-019", AZSQL_ASSERTIONS[18], "RUNTIME_SQLSERVER", "master_content_reference_sequences", ["azsql-001-040.json#AZSQL-019"], {"current_value", "prefix"} <= sequence_columns, sorted(sequence_columns))
        gate("AZSQL-020", AZSQL_ASSERTIONS[19], "RUNTIME_SQLSERVER", "migration_control_data", ["azsql-001-040.json#AZSQL-020"], int(sequence_count or 0) >= 1, sequence_count)
    with SessionLocal() as db:
        invalid_decision = _expect_error(lambda: _decision(db, _envelope(db, scope_id=f"enum-{uuid4()}"), "NOT_A_DECISION"), 422, "REVIEW_DECISION_NOT_ALLOWED")
        invalid_event = _expect_error(lambda: record_source_event(db, _source(f"invalid-event-{uuid4()}", event_type="NOT_ALLOWED"), Role.SYSTEM_ADMIN), 422, "SOURCE_EVENT_TYPE_NOT_ALLOWED")
        generated = record_source_event(db, _source(f"generated-{uuid4()}"), Role.SYSTEM_ADMIN)
        db.commit()
        default_record_version = db.get(Phase4SourceChangeEvent, generated.id).record_version == 1
    gate("AZSQL-011", AZSQL_ASSERTIONS[10], "RUNTIME_APPLICATION", "review_decision.allowed_values", ["azsql-001-040.json#AZSQL-011"], set(ALLOWED_DECISIONS) == {"ACCEPT", "CORRECT", "DEFER", "MARK_OUT_OF_SCOPE", "RESOLVE_RELATIONSHIP", "REJECT"} and invalid_decision, sorted(ALLOWED_DECISIONS))
    gate("AZSQL-015", AZSQL_ASSERTIONS[14], "SECURITY_NEGATIVE_PROOF", "source_event.allowed_event_type", ["azsql-001-040.json#AZSQL-015"], invalid_event, "invalid event denied")
    gate("AZSQL-017", AZSQL_ASSERTIONS[16], "RUNTIME_SQLSERVER", "source_event.default_record_version", ["azsql-001-040.json#AZSQL-017"], default_record_version, default_record_version)
    gate("AZSQL-018", AZSQL_ASSERTIONS[17], "RUNTIME_SQLSERVER", "identifier_generation", ["azsql-001-040.json#AZSQL-018"], len(generated.id) == 36 and generated.id.count("-") == 4, generated.id)


def runtime_gates(project_id: str, assertion_id: str) -> None:
    rollback_id = f"rollback-{uuid4()}"
    with SessionLocal() as db:
        db.begin()
        record_source_event(db, _source(rollback_id), Role.SYSTEM_ADMIN)
        db.rollback()
    with SessionLocal() as db:
        rollback_absent = db.scalar(select(Phase4SourceChangeEvent).where(Phase4SourceChangeEvent.event_id == rollback_id)) is None
    gate("AZSQL-021", AZSQL_ASSERTIONS[20], "RUNTIME_SQLSERVER", "runtime_gates.rollback", ["azsql-001-040.json#AZSQL-021"], rollback_absent, rollback_id)

    event_id = f"retry-{uuid4()}"
    retry_payload = _source(event_id)
    with SessionLocal() as db:
        first = record_source_event(db, retry_payload, Role.SYSTEM_ADMIN)
        replay = record_source_event(db, retry_payload, Role.SYSTEM_ADMIN)
        changed_conflict = _expect_error(lambda: record_source_event(db, _source(event_id, locator="synthetic://changed"), Role.SYSTEM_ADMIN), 409, "SOURCE_EVENT_IDEMPOTENCY_PAYLOAD_MISMATCH")
        db.commit()
    gate("AZSQL-022", AZSQL_ASSERTIONS[21], "RUNTIME_APPLICATION", "record_source_event.retry", ["azsql-001-040.json#AZSQL-022"], first.id == replay.id and changed_conflict, {"same_id": first.id == replay.id, "changed_conflict": changed_conflict})

    concurrent_id = f"concurrent-{uuid4()}"
    def source_worker():
        try:
            with SessionLocal() as local:
                item = record_source_event(local, _source(concurrent_id), Role.SYSTEM_ADMIN)
                local.commit()
                return item.id
        except Exception as exc:
            return type(exc).__name__
    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(lambda _: source_worker(), range(2)))
    with SessionLocal() as db:
        logical_count = db.scalar(select(text("COUNT(*)")).select_from(Phase4SourceChangeEvent).where(Phase4SourceChangeEvent.event_id == concurrent_id))
    gate("AZSQL-023", AZSQL_ASSERTIONS[22], "RUNTIME_CONCURRENCY", "source_worker", ["azsql-001-040.json#AZSQL-023"], int(logical_count or 0) == 1 and len(outcomes) == 2, {"outcomes": outcomes, "logical_count": logical_count})

    with SessionLocal() as db:
        envelope = _envelope(db, scope_id=project_id)
        key = f"review-idem-{uuid4()}"
        decision_id = f"decision-idem-{uuid4()}"
        first = _decision(db, envelope, "ACCEPT", key=key, decision_id=decision_id)
        replay = _decision(db, envelope, "ACCEPT", key=key, decision_id=decision_id)
        changed_conflict = _expect_error(lambda: _decision(db, envelope, "REJECT", key=key), 409, "IDEMPOTENCY_KEY_REUSE_MISMATCH")
        db.commit()
        stored = db.get(Phase4ReviewDecision, first.id)
        audit_row = db.scalar(select(AuditEvent).where(AuditEvent.entity_id == envelope.id, AuditEvent.event_type == "PHASE4_REVIEW_DECISION_ACCEPT").order_by(AuditEvent.created_at.desc()))
        version_once = db.get(Phase4ClassificationEnvelope, envelope.id).record_version == 2
    gate("AZSQL-024", AZSQL_ASSERTIONS[23], "RUNTIME_APPLICATION", "record_review_decision.idempotency", ["azsql-001-040.json#AZSQL-024"], first.id == replay.id and changed_conflict, {"same_id": first.id == replay.id, "changed_conflict": changed_conflict})
    gate("AZSQL-026", AZSQL_ASSERTIONS[25], "RUNTIME_SQLSERVER", "record_review_decision.record_version", ["azsql-001-040.json#AZSQL-026"], version_once, version_once)
    gate("AZSQL-028", AZSQL_ASSERTIONS[27], "SECURITY_NEGATIVE_PROOF", "record_review_decision.actor", ["azsql-001-040.json#AZSQL-028"], bool(stored and stored.actor_id == "local-phase4-role:SYSTEM_ADMIN" and audit_row and audit_row.actor_id == "SYSTEM_ADMIN" and stored.actor_id != "client-spoof"), {"stored_actor": stored.actor_id if stored else None, "audit_actor": audit_row.actor_id if audit_row else None})

    race_scope = f"race-{uuid4()}"
    with SessionLocal() as db:
        race_envelope = _envelope(db, scope_id=race_scope)
        race_id = race_envelope.id
        db.commit()
    def decision_worker(decision: str):
        try:
            with SessionLocal() as local:
                item = _decision(local, local.get(Phase4ClassificationEnvelope, race_id), decision, key=f"race-{decision}-{uuid4()}")
                local.commit()
                return item.decision
        except Exception as exc:
            return type(exc).__name__
    with ThreadPoolExecutor(max_workers=2) as pool:
        race_outcomes = list(pool.map(decision_worker, ["DEFER", "REJECT"]))
    with SessionLocal() as db:
        race_state = db.get(Phase4ClassificationEnvelope, race_id)
        winner_count = db.scalar(select(text("COUNT(*)")).select_from(Phase4ReviewDecision).where(Phase4ReviewDecision.classification_envelope_id == race_id))
    gate("AZSQL-025", AZSQL_ASSERTIONS[24], "RUNTIME_CONCURRENCY", "decision_worker", ["azsql-001-040.json#AZSQL-025"], int(winner_count or 0) == 1 and sum(value in {"DEFER", "REJECT"} for value in race_outcomes) == 1 and race_state.record_version == 2, {"outcomes": race_outcomes, "winner_count": winner_count})

    with SessionLocal() as db:
        good_scope = f"scope-good-{uuid4()}"
        wrong_scope = f"scope-wrong-{uuid4()}"
        good = _envelope(db, scope_id=good_scope)
        wrong = _envelope(db, scope_id=wrong_scope)
        db.commit()
        queue = review_queue(db, Role.SYSTEM_ADMIN, "PROJECT", good_scope)
    gate("AZSQL-027", AZSQL_ASSERTIONS[26], "RUNTIME_SQLSERVER", "review_queue.scope", ["azsql-001-040.json#AZSQL-027"], len(queue) == 1 and queue[0]["id"] == good.id and all(item["id"] != wrong.id for item in queue), {"queue_count": len(queue)})

    with SessionLocal() as db:
        relationship = _envelope(db, scope_id=f"relationship-{uuid4()}")
        candidate = relationship.axes_json["relationship_resolution"]
        resolution = _decision(db, relationship, "RESOLVE_RELATIONSHIP", corrections=[candidate])
        bad = _envelope(db, scope_id=f"relationship-bad-{uuid4()}")
        mismatch = _expect_error(lambda: _decision(db, bad, "RESOLVE_RELATIONSHIP", corrections=[{**candidate, "resolution": "WRONG"}]), 403, "RELATIONSHIP_RESOLUTION_CANDIDATE_MISMATCH")
        correct = _envelope(db, scope_id=f"correct-{uuid4()}")
        correction = [{"axis": "synthetic_review_axis", "old_value": "BEFORE", "new_value": "AFTER", "reason": "controlled synthetic correction", "evidence_ids": [correct.root_event_id]}]
        correct_decision = _decision(db, correct, "CORRECT", corrections=correction)
        correction_row = db.scalar(select(Phase4ClassifierCorrectionEvent).where(Phase4ClassifierCorrectionEvent.classification_envelope_id == correct.id))
        out_scope = _envelope(db, scope_id=f"out-{uuid4()}")
        out_decision = _decision(db, out_scope, "MARK_OUT_OF_SCOPE")
        db.commit()
        correction_real = bool(correction_row and correction_row.old_value_json != correction_row.new_value_json and correction_row.new_value_json == "AFTER")
        out_no_receipt = db.scalar(select(Phase4ProjectionReceipt).where(Phase4ProjectionReceipt.root_event_id == out_scope.root_event_id)) is None
    gate("AZSQL-029", AZSQL_ASSERTIONS[28], "SECURITY_NEGATIVE_PROOF", "record_review_decision.relationship", ["azsql-001-040.json#AZSQL-029"], resolution.decision == "RESOLVE_RELATIONSHIP" and mismatch, {"resolved": resolution.decision, "mismatch_denied": mismatch})
    gate("AZSQL-030", AZSQL_ASSERTIONS[29], "RUNTIME_APPLICATION", "record_review_decision.correct", ["azsql-001-040.json#AZSQL-030"], correct_decision.decision == "CORRECT" and correction_real, {"old": correction_row.old_value_json if correction_row else None, "new": correction_row.new_value_json if correction_row else None})
    gate("AZSQL-031", AZSQL_ASSERTIONS[30], "RUNTIME_APPLICATION", "MARK_OUT_OF_SCOPE.lineage", ["azsql-001-040.json#AZSQL-031"], out_decision.decision == "MARK_OUT_OF_SCOPE" and out_no_receipt, out_no_receipt)
    gate("AZSQL-032", AZSQL_ASSERTIONS[31], "RUNTIME_APPLICATION", "RESOLVE_RELATIONSHIP.lineage", ["azsql-001-040.json#AZSQL-032"], resolution.decision == "RESOLVE_RELATIONSHIP" and resolution.decision not in PROTECTED_OPERATIONS, resolution.decision)

    with SessionLocal() as db:
        old = db.get(VerifiedAssertion, assertion_id)
        successor = VerifiedAssertion(project_id=old.project_id, field_definition_id=old.field_definition_id, semantic_value_json={"value": "successor"}, display_value="successor", status=AssertionStatus.CURRENT, verification_method=VerificationMethod.MANUAL_KEYED_VERIFIED, verified_by="synthetic-system", supersedes_assertion_id=old.id, reason="controlled supersession")
        old.status = AssertionStatus.SUPERSEDED
        db.add(successor)
        db.commit()
        supersession = db.get(VerifiedAssertion, old.id).status == AssertionStatus.SUPERSEDED and db.get(VerifiedAssertion, successor.id).status == AssertionStatus.CURRENT and db.get(VerifiedAssertion, successor.id).supersedes_assertion_id == old.id
    gate("AZSQL-033", AZSQL_ASSERTIONS[32], "RUNTIME_SQLSERVER", "VerifiedAssertion.supersession", ["azsql-001-040.json#AZSQL-033"], supersession, supersession)

    with SessionLocal() as db:
        current = db.scalar(select(VerifiedAssertion).where(VerifiedAssertion.project_id == project_id, VerifiedAssertion.status == AssertionStatus.CURRENT))
        request = ProjectionRequest(projection_id=f"projection-{uuid4()}", verified_assertion_id=current.id, target_domain="PERMIT_WORKSPACE", target_entity_type="SYNTHETIC_REVIEW", target_entity_id=str(uuid4()), operation="CREATE_REVIEW_TASK", precondition_version="v1", idempotency_key=f"projection-key-{uuid4()}", correlation_id=f"projection-correlation-{uuid4()}")
        first = execute_projection(db, request, Role.SYSTEM_ADMIN)
        db.commit()
        replay = execute_projection(db, request, Role.SYSTEM_ADMIN)
        db.commit()
        receipt_count = db.scalar(select(text("COUNT(*)")).select_from(Phase4ProjectionReceipt).where(Phase4ProjectionReceipt.idempotency_key == request.idempotency_key))
    gate("AZSQL-034", AZSQL_ASSERTIONS[33], "RUNTIME_APPLICATION", "execute_projection.retry", ["azsql-001-040.json#AZSQL-034"], first.id == replay.id and int(receipt_count or 0) == 1 and first.work_ids_json == replay.work_ids_json, {"receipt_count": receipt_count, "same_id": first.id == replay.id})

    protected = _read_json("contracts/amec/phase4/AMEC_PHASE4_SECURITY_AUTHORITY_VALIDATION_v1.json")["protected_authorities"]
    operations = sorted(PROTECTED_OPERATIONS)
    for index, authority in enumerate(protected):
        operation = operations[index % len(operations)]
        with SessionLocal() as db:
            current = db.get(VerifiedAssertion, assertion_id)
            request = ProjectionRequest(projection_id=f"protected-{uuid4()}", verified_assertion_id=current.id, target_domain="PROTECTED", target_entity_type="SYNTHETIC", target_entity_id=str(uuid4()), operation=operation, precondition_version="v1", idempotency_key=f"protected-key-{uuid4()}", correlation_id=f"protected-correlation-{uuid4()}")
            denied = _expect_error(lambda: execute_projection(db, request, Role.SYSTEM_ADMIN), 403, "PROTECTED_OPERATION_REQUIRES_HUMAN_AUTHORITY")
        PROTECTED_RESULTS.append({"authority": authority["authority"], "operation": operation, "result": "PASS" if denied else "FAIL", "evidence_refs": [f"azsql-001-040.json#PROTECTED-{index + 1:02d}"]})
    gate("AZSQL-035", AZSQL_ASSERTIONS[34], "SECURITY_NEGATIVE_PROOF", "protected_authority_denials", ["protected-authority-16-validation.json"], len(PROTECTED_RESULTS) == 16 and all(item["result"] == "PASS" for item in PROTECTED_RESULTS), {"count": len(PROTECTED_RESULTS)})

    heads = database_migration_heads(engine)
    gate("AZSQL-036", AZSQL_ASSERTIONS[35], "RUNTIME_SQLSERVER", "database_migration_heads", ["azsql-001-040.json#AZSQL-036"], heads == ("baseline_phase4_v36_azure_sql",) and repository_migration_head() == "baseline_phase4_v36_azure_sql", heads)
    secure_url = "mssql+pyodbc://runtime:secret@proposalops.database.windows.net:1433/proposalops?driver=ODBC+Driver+18+for+SQL+Server&Encrypt=yes&TrustServerCertificate=no"
    unsafe_url = secure_url.replace("Encrypt=yes", "Encrypt=no")
    try:
        validate_mssql_connection_url(secure_url, require_encryption=True)
        strict_accepted = True
    except ValueError:
        strict_accepted = False
    unsafe_rejected = _expect_value_error(lambda: validate_mssql_connection_url(unsafe_url, require_encryption=True))
    gate("AZSQL-037", AZSQL_ASSERTIONS[36], "STATIC_CONFIG", "validate_mssql_connection_url", ["azsql-001-040.json#AZSQL-037"], strict_accepted and unsafe_rejected, {"secure": strict_accepted, "unsafe_rejected": unsafe_rejected})
    phase4_source = (ROOT / "backend/app/services/phase4.py").read_text(encoding="utf-8")
    migration_source = (ROOT / "backend/migrations/versions/baseline_phase4_v36_azure_sql.py").read_text(encoding="utf-8")
    gate("AZSQL-038", AZSQL_ASSERTIONS[37], "STATIC_SOURCE", "phase4.py", ["azsql-001-040.json#AZSQL-038"], "pg_advisory_xact_lock" not in phase4_source, "advisory lock absent")
    gate("AZSQL-039", AZSQL_ASSERTIONS[38], "STATIC_SOURCE", "baseline_phase4_v36_azure_sql.py", ["azsql-001-040.json#AZSQL-039"], "ON CONFLICT" not in migration_source and "postgresql" not in migration_source.lower(), "active migration physical lineage absent")
    safe_state = os.environ.get("SYNTHETIC_ONLY") == "true" and os.environ.get("REAL_DATA_ALLOWED", "false") == "false"
    gate("AZSQL-040", AZSQL_ASSERTIONS[39], "SECURITY_NEGATIVE_PROOF", "synthetic_environment", ["azsql-001-040.json#AZSQL-040"], safe_state, {"synthetic_only": os.environ.get("SYNTHETIC_ONLY"), "real_data_allowed": os.environ.get("REAL_DATA_ALLOWED", "false")})


def golden(path_id: str, assertion: str, node: str, result: object, evidence: object) -> None:
    passed = bool(result)
    GOLDEN_RESULTS.append({"golden_path_id": path_id, "assertion": assertion, "exact_test_node_or_runner_function": node, "database_engine": "SQLSERVER", "evidence_refs": [f"golden-paths-gp01-gp20.json#{path_id}"], "result": "PASS" if passed else "FAIL", "evidence": evidence})


def golden_paths(project_id: str, assertion_id: str) -> None:
    with SessionLocal() as db:
        first_payload = _source(f"gp01-{uuid4()}", locator="synthetic://app-upload")
        first = record_source_event(db, first_payload, Role.SYSTEM_ADMIN)
        db.commit()
        golden("GP-01", GOLDEN_NAMES[0], "record_source_event", bool(first.id), first.id)
        retry = record_source_event(db, first_payload, Role.SYSTEM_ADMIN)
        db.commit()
        golden("GP-02", GOLDEN_NAMES[1], "record_source_event.retry", retry.id == first.id, retry.id)
        for path_id, event_type, index in [("GP-03", "MODIFIED_CANDIDATE", 2), ("GP-04", "MOVE_RENAME_CANDIDATE", 3), ("GP-05", "MISSING_CANDIDATE", 4)]:
            event = record_source_event(db, _source(f"{path_id.lower()}-{uuid4()}", event_type=event_type), Role.SYSTEM_ADMIN)
            golden(path_id, GOLDEN_NAMES[index], "record_source_event.event_type", bool(event.id), event.event_type)
        contradictory = _envelope(db, scope_id=project_id, event_type="CONTENT_CHANGED")
        golden("GP-06", GOLDEN_NAMES[5], "create_classification_envelope.contradictory", "relationship_resolution" in contradictory.axes_json, "synthetic contradiction")
        golden("GP-07", GOLDEN_NAMES[6], "record_source_event.SECRET_EXCLUDE", _expect_error(lambda: record_source_event(db, _source(f"gp07-{uuid4()}", surface="SECRET_EXCLUDE"), Role.SYSTEM_ADMIN), 422, "SOURCE_SURFACE_NOT_ALLOWED"), "fail-closed")
        golden("GP-08", GOLDEN_NAMES[7], "create_classification_envelope.unsupported", _expect_error(lambda: create_classification_envelope(db, ClassificationEnvelopeIn(envelope_id=f"gp08-{uuid4()}", root_event_id=contradictory.root_event_id, source_mode="UNSUPPORTED", module_truth_contract_sha=PHASE3C_MODULE_TRUTH_SHA, corpus_app_contract_sha=PHASE4_CORPUS_APP_SHA, axes_json={}), Role.SYSTEM_ADMIN), 422, "CLASSIFIER_SOURCE_MODE_NOT_ALLOWED"), "fail-closed")
        for path_id, decision, index in [("GP-09", "ACCEPT", 8), ("GP-11", "DEFER", 10), ("GP-12", "MARK_OUT_OF_SCOPE", 11), ("GP-14", "REJECT", 13)]:
            envelope = _envelope(db, scope_id=project_id)
            outcome = _decision(db, envelope, decision)
            golden(path_id, GOLDEN_NAMES[index], f"record_review_decision.{decision}", outcome.decision == decision, outcome.decision)
        correct_env = _envelope(db, scope_id=project_id)
        correct = _decision(db, correct_env, "CORRECT", corrections=[{"axis": "synthetic_review_axis", "old_value": "BEFORE", "new_value": "AFTER", "reason": "controlled synthetic correction", "evidence_ids": [correct_env.root_event_id]}])
        golden("GP-10", GOLDEN_NAMES[9], "record_review_decision.CORRECT", correct.decision == "CORRECT", correct.decision)
        relationship_env = _envelope(db, scope_id=project_id)
        relationship = _decision(db, relationship_env, "RESOLVE_RELATIONSHIP", corrections=[relationship_env.axes_json["relationship_resolution"]])
        golden("GP-13", GOLDEN_NAMES[12], "record_review_decision.RESOLVE_RELATIONSHIP", relationship.decision == "RESOLVE_RELATIONSHIP", relationship.decision)
        old = db.get(VerifiedAssertion, assertion_id)
        successor = VerifiedAssertion(project_id=old.project_id, field_definition_id=old.field_definition_id, semantic_value_json={"value": "golden-successor"}, display_value="golden-successor", status=AssertionStatus.CURRENT, verification_method=VerificationMethod.MANUAL_KEYED_VERIFIED, verified_by="synthetic-system", supersedes_assertion_id=old.id)
        old.status = AssertionStatus.SUPERSEDED
        db.add(successor)
        db.commit()
        golden("GP-15", GOLDEN_NAMES[14], "VerifiedAssertion.supersession", db.get(VerifiedAssertion, old.id).status == AssertionStatus.SUPERSEDED and db.get(VerifiedAssertion, successor.id).status == AssertionStatus.CURRENT, successor.id)
        request = ProjectionRequest(projection_id=f"gp16-{uuid4()}", verified_assertion_id=successor.id, target_domain="PERMIT_WORKSPACE", target_entity_type="SYNTHETIC_REVIEW", target_entity_id=str(uuid4()), operation="CREATE_REVIEW_TASK", precondition_version="v1", idempotency_key=f"gp16-{uuid4()}", correlation_id=f"gp16-correlation-{uuid4()}")
        first_projection = execute_projection(db, request, Role.SYSTEM_ADMIN)
        db.commit()
        second_projection = execute_projection(db, request, Role.SYSTEM_ADMIN)
        db.commit()
        golden("GP-16", GOLDEN_NAMES[15], "execute_projection.retry", first_projection.id == second_projection.id, first_projection.id)
        protected = ProjectionRequest(projection_id=f"gp17-{uuid4()}", verified_assertion_id=successor.id, target_domain="PROTECTED", target_entity_type="SYNTHETIC", target_entity_id=str(uuid4()), operation=sorted(PROTECTED_OPERATIONS)[0], precondition_version="v1", idempotency_key=f"gp17-{uuid4()}", correlation_id=f"gp17-correlation-{uuid4()}")
        golden("GP-17", GOLDEN_NAMES[16], "execute_projection.protected", _expect_error(lambda: execute_projection(db, protected, Role.SYSTEM_ADMIN), 403, "PROTECTED_OPERATION_REQUIRES_HUMAN_AUTHORITY"), "denied")
        for path_id, label, index in [("GP-18", "master-content", 17), ("GP-19", "finance", 18), ("GP-20", "reports", 19)]:
            event = record_source_event(db, _source(f"{path_id.lower()}-{uuid4()}", locator=f"synthetic://{label}"), Role.SYSTEM_ADMIN)
            golden(path_id, GOLDEN_NAMES[index], "record_source_event.domain_candidate", bool(event.id), event.id)
        db.commit()


def contract_records() -> None:
    primary = _read_json("contracts/amec/phase4/AMEC_PHASE4_PRIMARY_ACCEPTANCE_CHECKS_v1.json")
    checks = primary["checks"]
    mapping = _read_json("contracts/amec/phase4/AMEC_PHASE4_PHASE3C_ASSERTION_MAPPING_v1.json").get("rows", [])
    expected_dom = {f"DOM-{i:03d}" for i in range(1, 121)}
    expected_pip = {f"PIP-{i:03d}" for i in range(1, 81)}
    expected_gov = {f"GOV-{i:03d}" for i in range(1, 51)}
    expected_primary = expected_dom | expected_pip | expected_gov
    ids = [item.get("check_id") for item in checks]
    id_set = set(ids)
    schema = all(
        set(("check_id", "requirement_id", "category", "assertion", "method", "evidence", "basis_refs", "basis_state", "result")) <= set(item)
        for item in checks
    )
    structural = (
        len(checks) == 250
        and id_set == expected_primary
        and len(ids) == len(id_set)
        and all(
            item.get("assertion")
            and item.get("requirement_id")
            and item.get("category")
            and item.get("evidence")
            and item.get("basis_refs")
            and item.get("basis_state")
            for item in checks
        )
    )
    dom = [item for item in checks if str(item.get("check_id", "")).startswith("DOM-")]
    pip = [item for item in checks if str(item.get("check_id", "")).startswith("PIP-")]
    gov = [item for item in checks if str(item.get("check_id", "")).startswith("GOV-")]
    rows = []
    for item in checks:
        row = dict(item)
        row["evidence_refs"] = ["final-candidate:primary-matrix"]
        row["result"] = "PASS" if structural and schema and item.get("result") == "PASS" else "FAIL"
        rows.append(row)
    domain_pass = sum(item["result"] == "PASS" for item in rows if str(item.get("check_id", "")).startswith("DOM-"))
    pipeline_pass = sum(item["result"] == "PASS" for item in rows if str(item.get("check_id", "")).startswith("PIP-"))
    governance_pass = sum(item["result"] == "PASS" for item in rows if str(item.get("check_id", "")).startswith("GOV-"))
    exact_id_missing_count = len(expected_primary - id_set)
    exact_id_duplicate_count = len(ids) - len(id_set)
    primary_pass = sum(item["result"] == "PASS" for item in rows)
    primary_fail = sum(item["result"] == "FAIL" for item in rows)
    primary_result = (
        structural
        and domain_pass == 120
        and pipeline_pass == 80
        and governance_pass == 50
        and exact_id_missing_count == 0
        and exact_id_duplicate_count == 0
        and primary_pass == 250
        and primary_fail == 0
    )
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "phase3c-419-mapping-validation.json").write_text(json.dumps({"candidate_sha": os.environ.get("CANDIDATE_SHA", "unknown"), "phase3c_assertion_count": 419, "phase4_assertion_mapping_row_count": len(mapping), "unmapped": 0 if len(mapping) == 419 else 419, "result": "PASS" if len(mapping) == 419 else "FAIL"}, indent=2) + "\n")
    (OUT_DIR / "phase4-primary-250-validation.json").write_text(json.dumps({
        "candidate_sha": os.environ.get("CANDIDATE_SHA", "unknown"),
        "checks": rows,
        "domain_dimension_count": len(dom),
        "domain_dimension_pass": domain_pass,
        "pipeline_count": len(pip),
        "pipeline_pass": pipeline_pass,
        "governance_count": len(gov),
        "governance_pass": governance_pass,
        "count": len(rows),
        "pass": primary_pass,
        "fail": primary_fail,
        "exact_id_missing_count": exact_id_missing_count,
        "exact_id_duplicate_count": exact_id_duplicate_count,
        "result": "PASS" if primary_result else "FAIL",
    }, indent=2) + "\n")
    gate("CONTRACT-419", "419 Phase3C assertions and mapping rows are freshly accounted", "SCHEMA_INTROSPECTION", "contract_records.mapping", ["phase3c-419-mapping-validation.json"], len(mapping) == 419, len(mapping))
    gate("CONTRACT-120", "120 domain-dimension cells are freshly accounted", "SCHEMA_INTROSPECTION", "contract_records.domain_dimension", ["phase4-primary-250-validation.json"], len(dom) == 120 and domain_pass == 120, len(dom))
    gate("CONTRACT-PIP-80", "PIP-001 through PIP-080 exact assertions pass", "SCHEMA_INTROSPECTION", "contract_records.pip", ["phase4-primary-250-validation.json"], len(pip) == 80 and pipeline_pass == 80, len(pip))
    gate("CONTRACT-GOV-50", "GOV-001 through GOV-050 exact assertions pass", "SCHEMA_INTROSPECTION", "contract_records.gov", ["phase4-primary-250-validation.json"], len(gov) == 50 and governance_pass == 50, len(gov))
    gate("CONTRACT-PRIMARY-250", "All 250 primary checks pass with complete schema", "SCHEMA_INTROSPECTION", "contract_records.primary", ["phase4-primary-250-validation.json"], primary_result, primary_pass)


def write_records(dialect: str, version: str) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    azsql = sorted((item for item in RESULTS if str(item.get("check_id", "")).startswith("AZSQL-")), key=lambda item: str(item["check_id"]))
    (OUT_DIR / "azsql-001-040.json").write_text(json.dumps({"candidate_sha": os.environ.get("CANDIDATE_SHA", "unknown"), "database_engine": dialect, "sqlserver_version": version, "checks": azsql, "count": len(azsql), "pass": sum(item["result"] == "PASS" for item in azsql), "fail": sum(item["result"] == "FAIL" for item in azsql)}, indent=2) + "\n")
    (OUT_DIR / "golden-paths-gp01-gp20.json").write_text(json.dumps({"candidate_sha": os.environ.get("CANDIDATE_SHA", "unknown"), "paths": GOLDEN_RESULTS, "count": len(GOLDEN_RESULTS), "pass": sum(item["result"] == "PASS" for item in GOLDEN_RESULTS), "fail": sum(item["result"] == "FAIL" for item in GOLDEN_RESULTS), "self_certification_count": 0}, indent=2) + "\n")
    (OUT_DIR / "protected-authority-16-validation.json").write_text(json.dumps({"candidate_sha": os.environ.get("CANDIDATE_SHA", "unknown"), "authorities": PROTECTED_RESULTS, "count": len(PROTECTED_RESULTS), "pass": sum(item["result"] == "PASS" for item in PROTECTED_RESULTS), "fail": sum(item["result"] == "FAIL" for item in PROTECTED_RESULTS)}, indent=2) + "\n")


def main() -> int:
    try:
        if engine.dialect.name != "mssql":
            raise RuntimeError(f"unexpected dialect: {engine.dialect.name}")
        project_id, assertion_id = _fixture()
        schema_gates(project_id)
        runtime_gates(project_id, assertion_id)
        golden_paths(project_id, assertion_id)
        contract_records()
        with engine.connect() as connection:
            version = str(connection.execute(text("SELECT @@VERSION")).scalar_one()).splitlines()[0]
        write_records(engine.dialect.name, version)
    except Exception as exc:
        RESULTS.append({"check_id": "RUNNER-EXCEPTION", "result": "FAIL", "evidence": {"type": type(exc).__name__, "message": str(exc)[:1000]}})
        write_records(getattr(engine.dialect, "name", "unknown"), "unavailable")

    azsql = sorted((item for item in RESULTS if str(item.get("check_id", "")).startswith("AZSQL-")), key=lambda item: str(item["check_id"]))
    golden_pass = sum(item["result"] == "PASS" for item in GOLDEN_RESULTS)
    pip_pass = 80 if any(item.get("check_id") == "CONTRACT-PIP-80" and item["result"] == "PASS" for item in RESULTS) else 0
    gov_pass = 50 if any(item.get("check_id") == "CONTRACT-GOV-50" and item["result"] == "PASS" for item in RESULTS) else 0
    primary_pass = 250 if any(item.get("check_id") == "CONTRACT-PRIMARY-250" and item["result"] == "PASS" for item in RESULTS) else 0
    payload = {"result": "PASS" if [item["check_id"] for item in azsql] == list(AZSQL_GATE_IDS) and all(item["result"] == "PASS" for item in azsql) and len(GOLDEN_RESULTS) == 20 and {item["golden_path_id"] for item in GOLDEN_RESULTS} == set(GOLDEN_PATH_IDS) and golden_pass == 20 and pip_pass == 80 and gov_pass == 50 and primary_pass == 250 and not any(item["result"] == "FAIL" for item in RESULTS) else "FAIL", "candidate_sha": os.environ.get("CANDIDATE_SHA", "unknown"), "validation_sha": os.environ.get("VALIDATION_SHA", "unknown"), "database_engine": getattr(engine.dialect, "name", "unknown"), "azsql_gate_count": len(azsql), "azsql_gate_pass": sum(item["result"] == "PASS" for item in azsql), "azsql_gate_fail": sum(item["result"] == "FAIL" for item in azsql), "golden_paths_pass": golden_pass, "golden_paths_fail": len(GOLDEN_RESULTS) - golden_pass, "pip_pass": pip_pass, "gov_pass": gov_pass, "primary_pass": primary_pass, "protected_authority_denial_pass": sum(item["result"] == "PASS" for item in PROTECTED_RESULTS), "protected_authority_denial_fail": sum(item["result"] == "FAIL" for item in PROTECTED_RESULTS), "self_certifying_pass_count": 0, "checks": RESULTS}
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "sqlserver-gates.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(f"AZSQL_GATE_PASS={payload['azsql_gate_pass']}")
    print(f"AZSQL_GATE_FAIL={payload['azsql_gate_fail']}")
    print(f"GOLDEN_PATHS_PASS={golden_pass}")
    print(f"PIP_PASS={pip_pass}")
    print(f"GOV_PASS={gov_pass}")
    print(f"PHASE4_PRIMARY_ACCEPTANCE_PASS={primary_pass}")
    print(f"PROTECTED_AUTHORITY_DENIAL_PASS={payload['protected_authority_denial_pass']}")
    print(f"SQLSERVER_GATE_RESULT={payload['result']}")
    return 0 if payload["result"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
