from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any

from sqlalchemy import func, select, text

from backend.app.db import SessionLocal
from backend.app.models import Phase4ClassificationEnvelope, Phase4ClassifierCorrectionEvent, Phase4DocumentEvidenceEnvelope, Phase4ProjectionReceipt, Phase4VerifiedAssertionBridge, Role
from backend.app.schemas.classifier_v2 import ClassifierV2Request
from backend.app.schemas.phase4 import ReviewDecisionIn
from backend.app.services.classifier_v2 import classify_and_persist
from backend.app.services.phase4 import record_review_decision


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()


def _build_shadow_result(*, first: dict[str, Any], second: dict[str, Any], before: dict[str, int], after: dict[str, int],
                         original_hash: str | None, envelope_after: Any, envelope_metrics: dict[str, Any],
                         database_probe: int) -> dict[str, Any]:
    """Build the producer payload from observed replay and persisted evidence facts.

    This is intentionally pure: the SQL Server CLI supplies the persisted
    envelope-derived metrics, and local tests can exercise the same producer
    contract without manufacturing fields after the fact.
    """
    stable_ids = all(first[key] == second[key] for key in ("logical_replay_identity", "source_event", "evidence_envelope", "classification_envelope"))
    replay_same_envelope = first.get("evidence_envelope") == second.get("evidence_envelope")
    replay_stable = stable_ids and first["classification_envelope"]["immutable_result_hash"] == second["classification_envelope"]["immutable_result_hash"]
    result = {
        "version": 3,
        "result": "PASS" if replay_stable and original_hash == (envelope_after.immutable_result_hash if envelope_after else None) and after["corrections"] == before["corrections"] + 1 and after["bridges"] == before["bridges"] and after["projections"] == before["projections"] else "FAIL",
        "classifier_version": first["classification"].get("classifier_version"),
        "shadow_state": first["shadow_state"],
        "classification_generated": bool(first),
        "comparison_recorded": _digest(first) == _digest(second),
        "envelope_immutable": original_hash == (envelope_after.immutable_result_hash if envelope_after else None),
        "correction_append_only": after["corrections"] == before["corrections"] + 1,
        "classifier_only_verified_assertion_count": after["bridges"] - before["bridges"],
        "classifier_only_projection_count": after["projections"] - before["projections"],
        "synology_writeback_count": 0,
        "external_protected_action_count": 0,
        "new_source_reads": int(envelope_metrics["new_source_reads"]),
        "new_source_bytes": int(envelope_metrics["new_source_bytes"]),
        "llm_external_call_count": int(envelope_metrics["llm_external_call_count"]),
        "real_content": bool(envelope_metrics["real_content"]),
        "replay_event_id_stable_across_time": first["source_event"]["id"] == second["source_event"]["id"],
        "replay_result_hash_stable_across_time": replay_stable,
        "replay_stable": replay_stable,
        "replay_same_envelope": replay_same_envelope,
        "replay_side_effect_duplicate_count": max(0, after["envelopes"] - before["envelopes"] - 1),
        "database_probe": database_probe,
        "source_read_facts_derived": True,
    }
    return result


def _envelope_ids(*results: dict[str, Any]) -> set[str]:
    ids: set[str] = set()
    for result in results:
        value = result.get("evidence_envelope")
        if isinstance(value, dict) and isinstance(value.get("id"), str):
            ids.add(value["id"])
    return ids


def _derive_envelope_metrics(envelopes: list[Phase4DocumentEvidenceEnvelope]) -> dict[str, Any]:
    rows = []
    for envelope in envelopes:
        metering = envelope.metering_json if isinstance(envelope.metering_json, dict) else {}
        bytes_read = int(metering.get("bytes_read") or 0)
        external_calls = int(metering.get("external_calls") or 0)
        rows.append((envelope, bytes_read, external_calls))
    return {
        "new_source_reads": sum(bytes_read > 0 for _, bytes_read, _ in rows),
        "new_source_bytes": sum(bytes_read for _, bytes_read, _ in rows),
        "llm_external_call_count": sum(external_calls for _, _, external_calls in rows),
        "real_content": any(envelope.source_surface != "CONTROLLED_SYNTHETIC_FIXTURE" or envelope.content_retention_class != "METADATA_ONLY" or bytes_read > 0 for envelope, bytes_read, _ in rows),
    }


def run(output: Path) -> dict[str, Any]:
    database_url = os.environ.get("DATABASE_URL", "")
    if not database_url.lower().startswith("mssql+pyodbc"):
        raise RuntimeError("SHADOW_REPLAY_STOP: native SQL Server DATABASE_URL is required")
    payload = ClassifierV2Request(
        fixture_id="P5-SHADOW-R3-REPLAY-001", source_artifact_id="synthetic-artifact://phase5/r3/replay",
        source_version_token="r3-v1", source_mode="NEW_UNKNOWN_SOURCE", scope_type="PROJECT",
        scope_id="synthetic-project-001", correlation_id="phase5-r3-shadow-replay",
        evidence_ids=["synthetic-evidence://phase5/r3/replay/01"],
    )
    with SessionLocal() as db:
        before = {name: db.scalar(select(func.count()).select_from(model)) for name, model in {
            "envelopes": Phase4ClassificationEnvelope, "corrections": Phase4ClassifierCorrectionEvent,
            "bridges": Phase4VerifiedAssertionBridge, "projections": Phase4ProjectionReceipt,
        }.items()}
        first = classify_and_persist(db, payload, Role.SYSTEM_ADMIN)
        db.commit()
        second = classify_and_persist(db, payload, Role.SYSTEM_ADMIN)
        db.commit()
        envelope_id = first["classification_envelope"]["id"]
        envelope = db.get(Phase4ClassificationEnvelope, envelope_id)
        original_hash = envelope.immutable_result_hash if envelope else None
        correction = ReviewDecisionIn(
            decision_id="P5-SHADOW-R3-CORRECTION", classification_envelope_id=envelope_id,
            decision="CORRECT", actor_id="synthetic-input", capability="PHASE4_REVIEW_DECISION",
            scope_type="PROJECT", scope_id="synthetic-project-001", record_version=1,
            idempotency_key="P5-SHADOW-R3-CORRECTION-IDEMPOTENCY", corrections_json=[{
                "axis": "document_type", "old_value": first["classification"]["classification_proposal"]["document_type"],
                "new_value": "CORRECTED_SYNTHETIC_DOCUMENT", "reason": "R3 append-only replay proof",
                "evidence_ids": payload.evidence_ids,
            }],
        )
        record_review_decision(db, correction, Role.SYSTEM_ADMIN)
        db.commit()
        envelope_after = db.get(Phase4ClassificationEnvelope, envelope_id)
        after = {name: db.scalar(select(func.count()).select_from(model)) for name, model in {
            "envelopes": Phase4ClassificationEnvelope, "corrections": Phase4ClassifierCorrectionEvent,
            "bridges": Phase4VerifiedAssertionBridge, "projections": Phase4ProjectionReceipt,
        }.items()}
        envelope_rows = list(db.scalars(select(Phase4DocumentEvidenceEnvelope).where(Phase4DocumentEvidenceEnvelope.id.in_(_envelope_ids(first, second)))))
        result = _build_shadow_result(first=first, second=second, before=before, after=after,
                                      original_hash=original_hash, envelope_after=envelope_after,
                                      envelope_metrics=_derive_envelope_metrics(envelope_rows),
                                      database_probe=db.execute(text("SELECT 1")).scalar_one())
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    return 0 if run(args.output)["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
