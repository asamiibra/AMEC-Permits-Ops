"""Deterministic read-only authority monitoring for the synthetic/approved-test path."""

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from fastapi.encoders import jsonable_encoder
from sqlalchemy import func, select, true
from sqlalchemy.orm import Session

from ..audit.service import audit
from ..fixtures.canonical import fixture_metadata
from ..models import *
from .week45 import row, stable_hash
from .week7 import create_routed_finding, now_utc


READ_OPERATIONS = ["READ_CURRENT_STATE", "READ_STATUS", "READ_COMMENTS"]
SAFE_RETRY_CLASSES = {"TRANSIENT_NETWORK", "PORTAL_UNAVAILABLE", "RATE_LIMIT"}
NO_RETRY_CLASSES = {"CONTRACT_DRIFT", "IDENTITY_MISMATCH", "PARSE_FAILURE", "AUTH_REQUIRED", "MFA_REQUIRED"}


def _status_value(value: Any) -> str:
    return getattr(value, "value", str(value))


def _comments(application: PermitApplication, override: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    if override and "comments" in override:
        return [jsonable_encoder(x) if isinstance(x, dict) else {"text": str(x)} for x in (override.get("comments") or [])]
    if _status_value(application.application_status) != "RETURNED":
        return []
    return [
        {"id": f"{application.external_request_number}:C1", "text": "Owner name differs from supporting document.", "language": "en"},
        {"id": f"{application.external_request_number}:C2", "text": "Drawing revision does not match package revision.", "language": "en"},
        {"id": f"{application.external_request_number}:C3", "text": "Required attachment missing.", "language": "en"},
    ]


def contract_payload(contract: PortalReadContract) -> dict[str, Any]:
    return {
        "route": contract.expected_route_or_section,
        "fields": contract.expected_field_keys,
        "status_semantics": contract.expected_status_semantics,
        "comment_structure": contract.expected_comment_structure,
        "identity": contract.expected_identity_assertions,
    }


def contract_fingerprint(contract: PortalReadContract) -> str:
    return stable_hash(contract_payload(contract))


def latest_contract(db: Session, policy: MonitoringPolicy, operation: str) -> PortalReadContract | None:
    return db.scalar(select(PortalReadContract).where(
        PortalReadContract.adapter_id == policy.adapter_id,
        PortalReadContract.adapter_version == policy.adapter_version,
        PortalReadContract.contract_version == policy.portal_contract_version,
        PortalReadContract.operation == operation,
        PortalReadContract.status == "ACTIVE",
    ).order_by(PortalReadContract.effective_from.desc()))


def _policy_decision(db: Session, policy: MonitoringPolicy, operation: str, *, run_id: str | None = None,
                    observed: dict[str, Any] | None = None) -> tuple[str, str, PortalReadContract | None]:
    if not policy.enabled or policy.status not in {"SYNTHETIC_ACTIVE", "APPROVED_TEST", "PRODUCTION_APPROVED"}:
        return "DENY", "POLICY_NOT_ACTIVE", latest_contract(db, policy, operation)
    if policy.environment == "PRODUCTION" and policy.status != "PRODUCTION_APPROVED":
        return "DENY", "PRODUCTION_READ_NOT_APPROVED", latest_contract(db, policy, operation)
    if operation not in (policy.operations_allowed or []):
        return "DENY", "OPERATION_NOT_ALLOWED", latest_contract(db, policy, operation)
    contract = latest_contract(db, policy, operation)
    if not contract:
        return "PAUSE_DRIFT", "READ_CONTRACT_MISSING", None
    observed_contract = (observed or {}).get("contract") or {}
    if observed_contract.get("fingerprint"):
        actual = str(observed_contract["fingerprint"])
    elif observed_contract.get("payload"):
        actual = stable_hash(observed_contract["payload"])
    else:
        actual = contract_fingerprint(contract)
    expected = contract.expected_structural_fingerprint
    if actual != expected:
        return "PAUSE_DRIFT", "CONTRACT_DRIFT", contract
    return "ALLOW", "CONTRACT_VALID", contract


def _new_cycle(db: Session, application: PermitApplication) -> SubmissionCycle:
    cycle = db.scalar(select(SubmissionCycle).where(SubmissionCycle.application_id == application.id).order_by(SubmissionCycle.cycle_number.desc()))
    if cycle:
        return cycle
    cycle = SubmissionCycle(application_id=application.id, cycle_number=max(1, application.repetition_count or 1), external_reference=f"MONITOR-{application.external_request_number}", status="MONITORING")
    db.add(cycle); db.flush()
    return cycle


def _status_event(db: Session, application: PermitApplication, *, event_type: str, source_reference: str,
                  payload: dict[str, Any], correlation_id: str) -> AuthorityEvent | None:
    payload_hash = stable_hash(payload)
    existing = db.scalar(select(AuthorityEvent).where(AuthorityEvent.application_id == application.id, AuthorityEvent.external_event_id == source_reference))
    if existing:
        return None
    event = AuthorityEvent(project_id=application.project_id, application_id=application.id, source_channel="READ_ONLY_MONITORING", source_type=event_type, external_reference=source_reference, external_event_id=source_reference, occurred_at=now_utc(), raw_evidence_artifact_id=f"synthetic://monitoring/{application.external_request_number}", payload_hash=payload_hash, normalized_key=f"{event_type}:{application.id}:{payload_hash}", status="NEW_EVENT", raw_payload=payload)
    db.add(event); db.flush()
    audit(db, correlation_id=correlation_id, event_type=event_type, entity_type="AuthorityEvent", entity_id=event.id, after={"event_type": event_type, "trusted": True}, metadata={**fixture_metadata(), "evidence_class": "SYNTHETIC_MEASURED"})
    return event


def _record_attempt(db: Session, notification: NotificationEvent | None) -> None:
    if not notification:
        return
    prior = db.scalar(select(func.max(NotificationDeliveryAttempt.attempt_number)).where(NotificationDeliveryAttempt.notification_event_id == notification.id)) or 0
    db.add(NotificationDeliveryAttempt(notification_event_id=notification.id, attempt_number=prior + 1, channel=notification.channel, attempted_at=notification.attempted_at or now_utc(), result="DELIVERED" if notification.status == NotificationStatus.DELIVERED else "FAILED", failure_code=notification.failure_code, external_reference=notification.external_message_reference))


def _state(application: PermitApplication, override: dict[str, Any] | None = None) -> dict[str, Any]:
    override = override or {}
    project = application.project
    status = _status_value(override.get("status", application.application_status))
    repetition = int(override.get("repetition_number", application.repetition_count or 0))
    comments = _comments(application, override)
    identity = {"application_id": application.id, "request_number": application.external_request_number, "project_id": application.project_id, "project_number": project.project_number if project else None, "municipality": application.municipality, "permit_type": application.permit_type}
    state = {"application_identity": identity, "status": status, "raw_status": _status_value(override.get("raw_status", status)), "repetition_number": repetition, "comments": comments, "portal_fields": override.get("portal_fields", {}), "attachment_fingerprint": override.get("attachment_fingerprint"), "grid_fingerprint": override.get("grid_fingerprint"), "captured_at": now_utc().isoformat()}
    return state


def _changed_paths(prior: dict[str, Any], current: dict[str, Any]) -> list[str]:
    changes = []
    for key in ["portal_fields", "attachment_fingerprint", "grid_fingerprint"]:
        if prior and prior.get(key) != current.get(key) and (prior.get(key) is not None or current.get(key) is not None):
            changes.append(key)
    return changes


def _comment_key(comment: dict[str, Any], application: PermitApplication) -> str:
    external = comment.get("id") or comment.get("external_comment_id")
    if external:
        return str(external)
    return f"HASH:{stable_hash({'request': application.external_request_number, 'text': comment.get('text', ''), 'section': comment.get('section_object_reference')})}"


def execute_monitoring_run(db: Session, policy: MonitoringPolicy, *, scheduled_for: datetime | None = None,
                           correlation_id: str | None = None, observed_override: dict[str, Any] | None = None,
                           capture_method: str = "AUTOMATED_READ") -> dict[str, Any]:
    application = db.get(PermitApplication, policy.application_id) if policy.application_id else None
    if not application:
        raise ValueError("MONITORING_APPLICATION_REQUIRED")
    correlation_id = correlation_id or str(uuid4())
    now = now_utc()
    due = scheduled_for or now
    existing = db.scalar(select(MonitoringRun).where(MonitoringRun.application_id == application.id, MonitoringRun.monitoring_policy_id == policy.id, MonitoringRun.scheduled_for == due, MonitoringRun.status.in_(["SCHEDULED", "RUNNING"])))
    if existing:
        return {"run": existing, "duplicate_claim_suppressed": True}
    run = MonitoringRun(application_id=application.id, monitoring_policy_id=policy.id, scheduled_for=due, started_at=now, environment=policy.environment, adapter_id=policy.adapter_id, adapter_version=policy.adapter_version, portal_contract_version=policy.portal_contract_version, status="RUNNING", correlation_id=correlation_id)
    db.add(run); db.flush()
    audit(db, correlation_id=correlation_id, event_type="MONITORING_RUN_STARTED", entity_type="MonitoringRun", entity_id=run.id, after={"application_id": application.id, "operations": READ_OPERATIONS}, metadata=fixture_metadata())
    decisions = []
    contracts: dict[str, PortalReadContract | None] = {}
    for operation in READ_OPERATIONS:
        decision, reason, contract = _policy_decision(db, policy, operation, run_id=run.id, observed=observed_override)
        contracts[operation] = contract
        item = MonitoringExecutionDecision(monitoring_policy_id=policy.id, run_id=run.id, operation=operation, decision=decision, reason_code=reason, policy_version=policy.version, adapter_version=policy.adapter_version)
        db.add(item); db.flush(); decisions.append(item)
        audit(db, correlation_id=correlation_id, event_type="MONITORING_READ_ALLOWED" if decision == "ALLOW" else "MONITORING_READ_DENIED", entity_type="MonitoringExecutionDecision", entity_id=item.id, after={"operation": operation, "decision": decision, "reason_code": reason}, metadata=fixture_metadata())
    if any(x.decision != "ALLOW" for x in decisions):
        reason = next(x.reason_code for x in decisions if x.decision != "ALLOW")
        if reason == "CONTRACT_DRIFT":
            observed_contract = (observed_override or {}).get("contract", {})
            expected = contracts["READ_CURRENT_STATE"].expected_structural_fingerprint if contracts["READ_CURRENT_STATE"] else "MISSING"
            actual = str(observed_contract.get("fingerprint") or stable_hash(observed_contract.get("payload", {})))
            drift = PortalDriftEvent(monitoring_run_id=run.id, adapter_id=policy.adapter_id, adapter_version=policy.adapter_version, operation="READ_CURRENT_STATE", drift_type=str(observed_contract.get("drift_type", "UNKNOWN_CONTRACT_DRIFT")), expected_fingerprint=expected, observed_fingerprint=actual, evidence_artifact_id=f"synthetic://monitoring/{run.id}/raw", severity="HIGH", status="OPEN")
            db.add(drift); db.flush(); policy.status = "DRIFTED"; policy.enabled = False; run.status = "DRIFTED"; run.result = "DRIFT_DETECTED"; run.completed_at = now
            audit(db, correlation_id=correlation_id, event_type="PORTAL_READ_DRIFT_DETECTED", entity_type="PortalDriftEvent", entity_id=drift.id, after={"trusted_parse": False, "fallback_mode": "ASSISTED_MANUAL_CAPTURE"}, metadata=fixture_metadata())
            audit(db, correlation_id=correlation_id, event_type="PORTAL_READ_PATH_PAUSED", entity_type="MonitoringPolicy", entity_id=policy.id, after={"status": policy.status}, metadata=fixture_metadata())
            db.commit()
            return {"run": run, "decisions": decisions, "result": "DRIFT_DETECTED", "trusted": False, "manual_fallback": True, "drift": drift, "maintainer_notification": True}
        run.status = "PAUSED" if reason in {"POLICY_NOT_ACTIVE", "PRODUCTION_READ_NOT_APPROVED"} else "FALLBACK_REQUIRED"
        run.result = "MANUAL_CAPTURE_REQUIRED" if reason not in {"POLICY_NOT_ACTIVE", "PRODUCTION_READ_NOT_APPROVED"} else "READ_FAILED"
        run.completed_at = now; db.commit()
        return {"run": run, "decisions": decisions, "result": run.result, "trusted": False, "manual_fallback": True}
    if (observed_override or {}).get("identity_mismatch"):
        run.status = "FAILED"; run.result = "READ_FAILED"; run.retry_class = "IDENTITY_MISMATCH"; run.completed_at = now; policy.failure_count += 1
        if policy.failure_count >= policy.max_failures_before_pause:
            policy.enabled = False; policy.status = "PAUSED"
        audit(db, correlation_id=correlation_id, event_type="MONITORING_RUN_FAILED", entity_type="MonitoringRun", entity_id=run.id, after={"reason_code": "IDENTITY_MISMATCH", "retry": False}, metadata=fixture_metadata()); db.commit()
        return {"run": run, "result": run.result, "trusted": False, "retry": False, "reason": "IDENTITY_MISMATCH"}
    if (observed_override or {}).get("failure_class"):
        failure_class = str(observed_override["failure_class"])
        run.status = "FAILED"; run.result = "READ_FAILED"; run.retry_class = failure_class; run.completed_at = now; policy.failure_count += 1
        if policy.failure_count >= policy.max_failures_before_pause:
            policy.enabled = False; policy.status = "PAUSED"; audit(db, correlation_id=correlation_id, event_type="MONITORING_POLICY_PAUSED", entity_type="MonitoringPolicy", entity_id=policy.id, after={"reason": "FAILURE_BUDGET", "failure_count": policy.failure_count}, metadata=fixture_metadata())
        audit(db, correlation_id=correlation_id, event_type="MONITORING_RUN_FAILED", entity_type="MonitoringRun", entity_id=run.id, after={"reason_code": failure_class, "retry": failure_class in SAFE_RETRY_CLASSES}, metadata=fixture_metadata()); db.commit()
        return {"run": run, "result": run.result, "trusted": False, "retry": failure_class in SAFE_RETRY_CLASSES, "reason": failure_class}
    state = _state(application, observed_override)
    current_hash = stable_hash({k: v for k, v in state.items() if k != "captured_at"})
    current_contract = contracts["READ_CURRENT_STATE"]
    previous = db.scalar(select(MonitoringStateSnapshot).where(MonitoringStateSnapshot.application_id == application.id, MonitoringStateSnapshot.trusted == true()).order_by(MonitoringStateSnapshot.captured_at.desc()))
    run.prior_snapshot_id = previous.id if previous else None
    snapshot = MonitoringStateSnapshot(application_id=application.id, monitoring_run_id=run.id, capture_method=capture_method, trusted=True, application_identity=state["application_identity"], state=state, raw_evidence={"source": "mock-authority", "state": state}, contract_fingerprint=current_contract.expected_structural_fingerprint if current_contract else "", state_hash=current_hash)
    db.add(snapshot); db.flush(); run.new_snapshot_id = snapshot.id
    prior_state = previous.state if previous else None
    prior_comments = { _comment_key(x, application): x for x in (prior_state or {}).get("comments", []) }
    current_comments = { _comment_key(x, application): x for x in state.get("comments", []) }
    new_keys = sorted(set(current_comments) - set(prior_comments))
    changed_keys = sorted(k for k in set(current_comments) & set(prior_comments) if current_comments[k].get("text") != prior_comments[k].get("text"))
    prior_status = (prior_state or {}).get("status")
    prior_rep = (prior_state or {}).get("repetition_number")
    status_changed = bool(previous and prior_status != state["status"])
    repetition_changed = bool(previous and prior_rep != state["repetition_number"])
    reasons = []
    if status_changed: reasons.append(f"STATUS:{prior_status}->{state['status']}")
    if repetition_changed: reasons.append(f"REPETITION:{prior_rep}->{state['repetition_number']}")
    if new_keys: reasons.append("NEW_OFFICIAL_COMMENT")
    if _status_value(state["status"]) in {"RETURNED", "APPROVED"}: reasons.append(f"AUTHORITY_STATE:{state['status']}")
    material = status_changed or repetition_changed or bool(new_keys)
    result = "MATERIAL_CHANGE" if material else "NO_CHANGE" if previous else "NON_MATERIAL_CHANGE"
    comparison = AuthorityStateComparison(monitoring_run_id=run.id, prior_snapshot_id=previous.id if previous else None, current_snapshot_id=snapshot.id, status_changed=status_changed, prior_status=prior_status, current_status=state["status"], repetition_changed=repetition_changed, prior_repetition=prior_rep, current_repetition=state["repetition_number"], new_comment_ids=new_keys, removed_comment_ids=sorted(set(prior_comments) - set(current_comments)), changed_comment_ids=changed_keys, materiality="MATERIAL" if material else "NONE", result=result, reasons=reasons)
    db.add(comparison); db.flush()
    for operation in READ_OPERATIONS:
        db.add(MonitoringCheck(monitoring_run_id=run.id, operation=operation, prior_fingerprint=previous.contract_fingerprint if previous else None, current_fingerprint=snapshot.contract_fingerprint, comparison_result=result, evidence_artifact_id=f"synthetic://monitoring/{run.id}/{operation}", status_code=state["raw_status"], repetition_number=state["repetition_number"], comment_count=len(current_comments), normalized_state_hash=current_hash))
    status_observation = AuthorityStatusObservation(application_id=application.id, monitoring_run_id=run.id, raw_status=state["raw_status"], normalized_status=state["status"], authority_reference=application.external_request_number, repetition_number=state["repetition_number"], evidence_artifact_id=f"synthetic://monitoring/{run.id}/status", source_hash=stable_hash({"status": state["raw_status"], "repetition": state["repetition_number"]}))
    db.add(status_observation)
    for key, comment in current_comments.items():
        observation = AuthorityCommentObservation(application_id=application.id, monitoring_run_id=run.id, external_comment_id=comment.get("id"), raw_text=comment.get("text", ""), language=comment.get("language", "ar" if any("\u0600" <= c <= "\u06ff" for c in comment.get("text", "")) else "en"), authority_reference=application.external_request_number, section_object_reference=comment.get("section_object_reference"), evidence_artifact_id=f"synthetic://monitoring/{run.id}/comment/{key}", source_hash=stable_hash(comment), normalized_key=key)
        db.add(observation)
    created = []
    if material:
        event_type = "AUTHORITY_APPROVED" if state["status"] == "APPROVED" else "AUTHORITY_RETURNED" if state["status"] == "RETURNED" else "STATUS_CHANGED" if status_changed else "REPETITION_CHANGED"
        event = _status_event(db, application, event_type=event_type, source_reference=f"MONITOR:{application.id}:{current_hash}", payload={"status": state["status"], "repetition": state["repetition_number"], "comparison_id": comparison.id}, correlation_id=correlation_id)
        if event: created.append(event)
    for key in new_keys:
        cycle = _new_cycle(db, application)
        comment = current_comments[key]
        routed = create_routed_finding(db, project=application.project, application=application, source_type=FindingSourceType.OFFICIAL_MUNICIPALITY_COMMENT, source_channel="READ_ONLY_MONITORING", source_reference=f"MONITOR-COMMENT:{key}", raw_text=comment.get("text", ""), title="New authority comment", normalized_summary=comment.get("text", ""), language=comment.get("language", "en"), submission_cycle_id=cycle.id, external_event_id=f"MONITOR-COMMENT:{key}", occurred_at=comment.get("occurred_at"), evidence_artifact_id=f"synthetic://monitoring/{run.id}/comment/{key}", finding_code="OTHER_AUTHORITY_COMMENT", discipline="GENERAL", correlation_id=correlation_id, captured_by="monitoring-adapter", normalized_key=f"MONITOR-COMMENT:{key}", raw_payload={"monitoring_run_id": run.id, "comment_key": key})
        _record_attempt(db, routed.get("notification")); created.append(routed)
    mutation_paths = _changed_paths((prior_state or {}), state)
    if mutation_paths:
        mutation = ExternalMutationObservation(application_id=application.id, monitoring_run_id=run.id, prior_snapshot_id=previous.id if previous else None, current_snapshot_id=snapshot.id, changed_paths=mutation_paths, prior_values={x: (prior_state or {}).get(x) for x in mutation_paths}, observed_values={x: state.get(x) for x in mutation_paths}, impact="RECONCILIATION_REQUIRED", evidence_artifact_id=f"synthetic://monitoring/{run.id}/external-mutation", authorship="EXTERNAL_HUMAN_OR_AUTHORITY")
        db.add(mutation); db.flush(); audit(db, correlation_id=correlation_id, event_type="EXTERNAL_MUTATION_DETECTED", entity_type="ExternalMutationObservation", entity_id=mutation.id, after={"changed_paths": mutation_paths, "authorship": mutation.authorship}, metadata=fixture_metadata())
        from .week8 import record_material_change
        record_material_change(db, project_id=application.project_id, source_type="ExternalPortalState", source_id=mutation.id, previous_version_or_hash=previous.state_hash if previous else None, new_version_or_hash=snapshot.state_hash, change_type="EXTERNAL_PORTAL_MUTATION", material=True, actor_or_system="EXTERNAL_HUMAN_OR_AUTHORITY", correlation_id=correlation_id, metadata={"changed_paths": mutation_paths, "authorship": mutation.authorship})
    run.status = "COMPLETED"; run.result = result; run.completed_at = now; run.duration_ms = max(0, int((now - run.started_at).total_seconds() * 1000))
    audit(db, correlation_id=correlation_id, event_type="MONITORING_NO_CHANGE" if result == "NO_CHANGE" else "MONITORING_MATERIAL_CHANGE", entity_type="MonitoringRun", entity_id=run.id, after={"result": result, "trusted": True, "new_comments": len(new_keys)}, metadata=fixture_metadata())
    db.commit()
    return {"run": run, "snapshot": snapshot, "comparison": comparison, "result": result, "trusted": True, "new_comments": new_keys, "authority_events": created, "finding_count": sum(1 for x in created if isinstance(x, dict) and x.get("finding")), "external_mutation": bool(mutation_paths), "decisions": decisions}


def due_run(db: Session, *, policy_id: str | None = None, application_id: str | None = None, observed_override: dict[str, Any] | None = None, correlation_id: str | None = None) -> dict[str, Any]:
    stmt = select(MonitoringPolicy).where(MonitoringPolicy.enabled == true(), MonitoringPolicy.status.in_(["SYNTHETIC_ACTIVE", "APPROVED_TEST", "PRODUCTION_APPROVED"]))
    if policy_id: stmt = stmt.where(MonitoringPolicy.id == policy_id)
    if application_id: stmt = stmt.where(MonitoringPolicy.application_id == application_id)
    policy = db.scalar(stmt.order_by(MonitoringPolicy.effective_from))
    if not policy:
        return {"runs": [], "reason": "NO_DUE_ACTIVE_POLICY"}
    return {"runs": [execute_monitoring_run(db, policy, observed_override=observed_override, correlation_id=correlation_id)]}


def manual_capture(db: Session, payload: dict[str, Any], *, correlation_id: str) -> dict[str, Any]:
    application = db.get(PermitApplication, payload.get("application_id"))
    if not application:
        raise ValueError("APPLICATION_NOT_FOUND")
    capture = HumanMonitoringCapture(application_id=application.id, submission_cycle_id=payload.get("submission_cycle_id"), captured_by=payload.get("captured_by", "authorized-human"), status=payload.get("status", "UNKNOWN_REVIEW_REQUIRED"), repetition_number=payload.get("repetition_number"), comments=payload.get("comments", []), evidence_artifact_ids=payload.get("evidence_artifact_ids", []), verification_mode="HUMAN_EVIDENCE", evidence_class=payload.get("evidence_class", "HUMAN_EVIDENCE"))
    db.add(capture); db.flush(); audit(db, correlation_id=correlation_id, event_type="PORTAL_READ_MANUAL_FALLBACK", entity_type="HumanMonitoringCapture", entity_id=capture.id, after={"application_id": application.id, "evidence_level": capture.evidence_class}, metadata=fixture_metadata())
    policy = db.scalar(select(MonitoringPolicy).where(MonitoringPolicy.application_id == application.id).order_by(MonitoringPolicy.effective_from))
    if not policy:
        policy = MonitoringPolicy(application_id=application.id, environment="TEST", enabled=False, evidence_class="HUMAN_EVIDENCE", operations_allowed=READ_OPERATIONS, cadence_mode="MANUAL", adapter_id="human-assisted", adapter_version="W11-1.0", portal_contract_version="HUMAN-EVIDENCE", fallback_mode="ASSISTED_MANUAL_CAPTURE", status="PAUSED")
        db.add(policy); db.flush()
    observed = {"status": capture.status, "repetition_number": capture.repetition_number, "comments": capture.comments}
    was_enabled, was_status = policy.enabled, policy.status
    policy.enabled, policy.status = True, "SYNTHETIC_ACTIVE"
    result = execute_monitoring_run(db, policy, observed_override=observed, capture_method="HUMAN_EVIDENCE", correlation_id=correlation_id)
    policy.enabled, policy.status = was_enabled, was_status
    db.commit()
    return {"capture": capture, "monitoring": result, "fixture": fixture_metadata()}


def metrics(db: Session) -> dict[str, Any]:
    runs = list(db.scalars(select(MonitoringRun)).all()); checks = list(db.scalars(select(MonitoringCheck)).all()); drifts = list(db.scalars(select(PortalDriftEvent)).all()); fallbacks = sum(x.result == "MANUAL_CAPTURE_REQUIRED" for x in runs) + len([x for x in db.scalars(select(HumanMonitoringCapture)).all()])
    timings = list(db.scalars(select(OperatorTaskTiming)).all())
    durations = sorted(x.duration_ms for x in runs if x.duration_ms is not None)
    timing_summary = {}
    for source in sorted({x.source for x in timings}):
        values = sorted(x.duration_ms for x in timings if x.source == source)
        if values:
            timing_summary[source] = {
                "sample_count": len(values),
                "median_duration_ms": values[(len(values) - 1) // 2],
                "p95_duration_ms": values[max(0, int(len(values) * 0.95) - 1)],
                "median_correction_count": sorted(x.correction_count for x in timings if x.source == source)[(len(values) - 1) // 2],
            }
    monitoring_events = db.scalar(select(func.count(AuthorityEvent.id)).where(AuthorityEvent.source_channel == "READ_ONLY_MONITORING")) or 0
    monitoring_findings = db.scalar(select(func.count(Finding.id)).join(AuthorityEvent, Finding.authority_event_id == AuthorityEvent.id).where(AuthorityEvent.source_channel == "READ_ONLY_MONITORING")) or 0
    return {"label": "DEMONSTRATION BASELINE — SYNTHETIC DATA — NOT CLIENT APPROVED", "monitoring_runs_due": sum(x.status == "SCHEDULED" for x in runs), "monitoring_runs_completed": sum(x.status == "COMPLETED" for x in runs), "no_change_checks": sum(x.comparison_result == "NO_CHANGE" for x in checks), "material_change_events": sum(x.result == "MATERIAL_CHANGE" for x in runs), "failed_runs": sum(x.status == "FAILED" for x in runs), "paused_policies": sum(x.status in {"PAUSED", "DRIFTED"} for x in db.scalars(select(MonitoringPolicy)).all()), "drifted_adapters": len(drifts), "manual_fallbacks": fallbacks, "average_read_duration_ms": sum(durations) / len(durations) if durations else None, "p95_read_duration_ms": durations[max(0, int(len(durations) * 0.95) - 1)] if durations else None, "new_comments_detected": sum(len(x.new_comment_ids) for x in db.scalars(select(AuthorityStateComparison)).all()), "duplicate_comments_suppressed": max(0, sum(1 for x in db.scalars(select(AuthorityCommentObservation)).all()) - sum(len(x.new_comment_ids) for x in db.scalars(select(AuthorityStateComparison)).all())), "authority_events_created": monitoring_events, "findings_created": monitoring_findings, "timing_sample": len(timings), "timing_summary": timing_summary, "fixture": fixture_metadata()}
