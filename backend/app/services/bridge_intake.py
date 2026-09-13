"""Governed synthetic/source-bridge package intake.

The bridge is machine-authenticated and integrity-checked, but it only creates
source/evidence/classifier/observation candidates.  Human review remains the
only path to VerifiedAssertion or a typed business projection.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.exceptions import InvalidSignature
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..audit.service import audit
from ..models import (
    AssertionStatus,
    Document,
    DocumentApprovalState,
    DocumentType,
    DocumentVersion,
    ExtractionMethod,
    FieldDefinition,
    FieldObservation,
    Phase4ClassificationEnvelope,
    Phase4DocumentEvidenceEnvelope,
    Phase4SourceChangeEvent,
    Project,
)
from ..schemas.bridge_intake import BridgePackageIn
from ..services.classifier_v2 import (
    CLASSIFIER_VERSION,
    RULES_VERSION,
    TAXONOMY_REVISION,
    classify_document,
)
from ..services.document_intelligence import normalize_classifier_proposal, normalize_field_observation
from ..schemas.classifier_v2 import ClassifierV2Request
from ..services.phase4 import PHASE3C_MODULE_TRUTH_SHA, PHASE4_CORPUS_APP_SHA
from ..models.base import utcnow
from ..auth.bridge import BridgeIdentity


MAX_DEFAULT_PAYLOAD_BYTES = 1_048_576


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def _sha(value: Any) -> str:
    return hashlib.sha256(_json(value).encode("utf-8")).hexdigest()


def _error(status: int, code: str, **details: Any) -> HTTPException:
    return HTTPException(status_code=status, detail={"code": code, **details})


def canonical_signature_payload(payload: BridgePackageIn) -> bytes:
    return _json({
        "attempt_id": payload.attempt_id,
        "source_identity": payload.source_identity,
        "source_path_snapshot": payload.source_path_snapshot,
        "size_bytes": payload.size_bytes,
        "mtime_utc": payload.mtime_utc,
        "payload_sha256": payload.payload_sha256,
        "source_version_token": payload.source_version_token,
        "correlation_id": payload.correlation_id,
        "source_mode": payload.source_mode,
        "scope_type": payload.scope_type,
        "scope_id": payload.scope_id,
        "project_id": payload.project_id,
        "field_definition_id": payload.field_definition_id,
        "field_raw_value": payload.field_raw_value,
        "source_filename": payload.source_filename,
        "mime_type": payload.mime_type,
    }).encode("utf-8")


def _decode_payload(payload: BridgePackageIn, settings) -> tuple[bytes, str]:
    try:
        raw = base64.b64decode(payload.payload_b64, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise _error(422, "BRIDGE_PAYLOAD_BASE64_INVALID") from exc
    maximum = int(getattr(settings, "bridge_max_payload_bytes", MAX_DEFAULT_PAYLOAD_BYTES) or MAX_DEFAULT_PAYLOAD_BYTES)
    if len(raw) > maximum:
        raise _error(413, "BRIDGE_PAYLOAD_TOO_LARGE", max_bytes=maximum)
    if len(raw) != payload.size_bytes:
        raise _error(422, "BRIDGE_SIZE_MISMATCH", declared=payload.size_bytes, observed=len(raw))
    digest = hashlib.sha256(raw).hexdigest()
    if digest != payload.payload_sha256:
        raise _error(422, "BRIDGE_HASH_MISMATCH")
    return raw, digest


def _validate_package(payload: BridgePackageIn, raw: bytes, settings) -> None:
    allowed_identities = {
        value.strip()
        for value in str(getattr(settings, "bridge_allowed_source_identities", "QATAR_SYNOLOGY_SYNTHETIC_FIXTURE")).split(",")
        if value.strip()
    }
    if payload.source_identity not in allowed_identities:
        raise _error(403, "BRIDGE_SOURCE_NOT_ALLOWLISTED")
    allowed_prefixes = tuple(
        value.strip()
        for value in str(getattr(settings, "bridge_allowed_source_path_prefixes", "synthetic://qatar-synology/")).split(",")
        if value.strip()
    )
    if not any(payload.source_path_snapshot.startswith(prefix) for prefix in allowed_prefixes):
        raise _error(403, "BRIDGE_SOURCE_PATH_NOT_ALLOWLISTED")
    if payload.scope_type != "PROJECT" or payload.scope_id != payload.project_id:
        raise _error(422, "BRIDGE_PROJECT_SCOPE_MISMATCH")
    public_key_b64 = str(getattr(settings, "bridge_package_signing_public_key", "")).strip()
    if not public_key_b64:
        raise _error(503, "BRIDGE_SIGNING_KEY_NOT_CONFIGURED")
    try:
        public_key = Ed25519PublicKey.from_public_bytes(base64.b64decode(public_key_b64, validate=True))
        signature = base64.b64decode(payload.signature_b64, validate=True)
        public_key.verify(signature, canonical_signature_payload(payload))
    except (ValueError, binascii.Error, InvalidSignature) as exc:
        raise _error(422, "BRIDGE_SIGNATURE_INVALID") from exc
    del raw


def _existing_result(db: Session, event: Phase4SourceChangeEvent) -> dict[str, Any] | None:
    evidence = db.scalar(select(Phase4DocumentEvidenceEnvelope).where(Phase4DocumentEvidenceEnvelope.root_event_id == event.id))
    if evidence is None:
        return None
    classification = db.scalar(select(Phase4ClassificationEnvelope).where(Phase4ClassificationEnvelope.root_event_id == event.id))
    document_version_id = evidence.evidence_json.get("document_version_id") if isinstance(evidence.evidence_json, dict) else None
    observation = None
    if document_version_id:
        observation = db.scalar(select(FieldObservation).where(FieldObservation.document_version_id == document_version_id).order_by(FieldObservation.observed_at))
    candidate_ids: list[str] = []
    if observation is not None:
        candidate_ids.append(normalize_field_observation(db, observation, evidence_envelope_id=evidence.id).id)
    if classification is not None:
        proof = event.content_identity_proof if isinstance(event.content_identity_proof, dict) else {}
        candidates = normalize_classifier_proposal(
            db,
            scope_type=proof.get("scope_type", "PROJECT"),
            scope_id=proof.get("scope_id", proof.get("project_id")),
            correlation_id=event.correlation_id,
            source_artifact_id=event.source_artifact_id_or_locator,
            proposal=classification.axes_json,
            classifier_version=classification.classifier_version,
            rules_version=classification.rules_version,
            taxonomy_revision=classification.taxonomy_revision,
            evidence_envelope_id=evidence.id,
            source_document_version_id=classification.document_version_id,
        )
        candidate_ids.extend(candidate.id for candidate in candidates)
    return {
        "result": "IDEMPOTENT",
        "attempt_id": event.event_id.removeprefix("bridge:"),
        "source_event_id": event.id,
        "evidence_envelope_id": evidence.id,
        "classification_envelope_id": classification.id if classification else None,
        "document_version_id": document_version_id,
        "field_observation_id": observation.id if observation else None,
        "candidate_assertion_ids": candidate_ids,
        "verified_assertion_created": False,
        "projection_created": False,
        "signature_verified": True,
        "package_sha256": (evidence.evidence_json or {}).get("package_sha256"),
    }


def ingest_bridge_package(db: Session, payload: BridgePackageIn, identity: BridgeIdentity, settings) -> dict[str, Any]:
    raw, package_sha256 = _decode_payload(payload, settings)
    _validate_package(payload, raw, settings)
    event_id = f"bridge:{payload.attempt_id}"
    event_content = {
        "event_id": event_id,
        "source_identity": payload.source_identity,
        "source_path_snapshot": payload.source_path_snapshot,
        "size_bytes": payload.size_bytes,
        "mtime_utc": payload.mtime_utc,
        "payload_sha256": package_sha256,
        "source_version_token": payload.source_version_token,
        "correlation_id": payload.correlation_id,
        "scope_type": payload.scope_type,
        "scope_id": payload.scope_id,
        "project_id": payload.project_id,
        "bridge_client_id": identity.client_id,
        "bridge_object_id": identity.object_id,
    }
    immutable_hash = _sha(event_content)
    existing_event = db.scalar(select(Phase4SourceChangeEvent).where(Phase4SourceChangeEvent.event_id == event_id))
    if existing_event:
        if existing_event.immutable_payload_hash != immutable_hash:
            raise _error(409, "BRIDGE_ATTEMPT_ID_REUSE_MISMATCH")
        existing = _existing_result(db, existing_event)
        if existing:
            return existing
        raise _error(409, "BRIDGE_ATTEMPT_STATE_INCOMPLETE")

    project = db.get(Project, payload.project_id)
    field_definition = db.get(FieldDefinition, payload.field_definition_id)
    if project is None or field_definition is None:
        raise _error(422, "BRIDGE_SYNTHETIC_TARGET_NOT_FOUND")

    document = Document(
        project_id=project.id,
        document_type=DocumentType.OTHER,
        logical_name=f"qatar-bridge:{payload.attempt_id}",
        language="und",
        source_system="QATAR_SOURCE_INTAKE_BRIDGE",
    )
    db.add(document)
    db.flush()
    version = DocumentVersion(
        document_id=document.id,
        version_number=1,
        source_filename=payload.source_filename,
        source_path_or_reference=payload.source_path_snapshot,
        sha256=package_sha256,
        mime_type=payload.mime_type,
        file_size=len(raw),
        language="und",
        approval_state=DocumentApprovalState.WORKING,
        source_system="QATAR_SOURCE_INTAKE_BRIDGE",
        metadata_json={
            "bridge_attempt_id": payload.attempt_id,
            "source_identity": payload.source_identity,
            "source_mtime_utc": payload.mtime_utc,
            "synthetic_non_business_fixture": True,
        },
        synthetic_content=raw,
    )
    db.add(version)
    db.flush()
    document.current_version_id = version.id

    event = Phase4SourceChangeEvent(
        event_id=event_id,
        scan_id_or_observation_group=f"bridge-scan:{payload.attempt_id}",
        source_surface="SYNOLOGY_EXTERNAL_EVIDENCE",
        source_artifact_id_or_locator=payload.source_path_snapshot,
        source_version_id=version.id,
        source_version_token=payload.source_version_token,
        event_type="NEW_VERSION",
        observed_size=len(raw),
        observed_mtime=payload.mtime_utc,
        origin="QATAR_SOURCE_INTAKE_BRIDGE",
        correlation_id=payload.correlation_id,
        observed_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        stability_state="STABLE",
        observation_count=1,
        stability_window_seconds=0,
        content_identity_proof={**event_content, "signature_verified": True},
        immutable_payload_hash=immutable_hash,
        record_version=1,
    )
    db.add(event)
    db.flush()

    evidence_hash = _sha({"event": event.id, "package_sha256": package_sha256, "attempt_id": payload.attempt_id})
    evidence = Phase4DocumentEvidenceEnvelope(
        root_event_id=event.id,
        source_artifact_id=payload.source_path_snapshot,
        source_version_id=version.id,
        source_version_token=payload.source_version_token,
        source_surface="SYNOLOGY_EXTERNAL_EVIDENCE",
        evidence_envelope_sha256=evidence_hash,
        document_intelligence_runtime_version="g10-bridge-package-v1",
        runtime_sha256=_sha({"runtime": "g10-bridge-package-v1"}),
        capability_id="G10_SOURCE_INTAKE_BRIDGE",
        handler_parser_identity="g10-synthetic-bridge-package-v1",
        metering_json={"external_calls": 0, "bytes_read": len(raw), "real_content": False},
        warnings_json=["SYNTHETIC_NON_BUSINESS_FIXTURE"],
        content_retention_class="SYNTHETIC_FIXTURE_BYTES",
        evidence_json={
            "attempt_id": payload.attempt_id,
            "document_version_id": version.id,
            "package_sha256": package_sha256,
            "source_identity": payload.source_identity,
            "source_path_snapshot": payload.source_path_snapshot,
            "size_bytes": len(raw),
            "mtime_utc": payload.mtime_utc,
            "signature_verified": True,
        },
    )
    db.add(evidence)
    db.flush()

    classifier_payload = ClassifierV2Request(
        fixture_id=f"g10-bridge:{payload.attempt_id}",
        source_artifact_id=payload.source_path_snapshot,
        source_version_token=payload.source_version_token,
        source_mode=payload.source_mode,
        scope_type=payload.scope_type,
        scope_id=payload.scope_id,
        correlation_id=payload.correlation_id,
        evidence_ids=[f"synthetic-evidence://g10-bridge/{payload.attempt_id}"],
        document_type_hint="CONTROLLED_SYNTHETIC_DOCUMENT",
        discipline_hint="ENGINEERING",
    )
    proposal = classify_document(classifier_payload)
    classification = Phase4ClassificationEnvelope(
        envelope_id=f"g10-bridge-classification:{payload.attempt_id}",
        root_event_id=event.id,
        document_version_id=version.id,
        source_mode="SYNOLOGY_EXTERNAL_EVIDENCE",
        classifier_version=CLASSIFIER_VERSION,
        rules_version=RULES_VERSION,
        taxonomy_revision=TAXONOMY_REVISION,
        module_truth_contract_sha=PHASE3C_MODULE_TRUTH_SHA,
        corpus_app_contract_sha=PHASE4_CORPUS_APP_SHA,
        axes_json=proposal,
        immutable_result_hash=_sha(proposal),
        record_version=1,
        status="PENDING_REVIEW",
    )
    db.add(classification)
    db.flush()

    observation = FieldObservation(
        project_id=project.id,
        field_definition_id=field_definition.id,
        document_version_id=version.id,
        raw_value=payload.field_raw_value,
        normalized_candidate_value=payload.field_raw_value,
        structured_value_json={"candidate_only": True, "bridge_attempt_id": payload.attempt_id},
        extraction_method=ExtractionMethod.IMPORT,
        extractor_version="g10-bridge-package-v1",
        confidence=0.0,
        correlation_id=payload.correlation_id,
    )
    db.add(observation)
    db.flush()
    candidates = [
        normalize_field_observation(db, observation, evidence_envelope_id=evidence.id),
        *normalize_classifier_proposal(
            db,
            scope_type=payload.scope_type,
            scope_id=payload.scope_id,
            correlation_id=payload.correlation_id,
            source_artifact_id=payload.source_path_snapshot,
            proposal=proposal,
            classifier_version=CLASSIFIER_VERSION,
            rules_version=RULES_VERSION,
            taxonomy_revision=TAXONOMY_REVISION,
            evidence_envelope_id=evidence.id,
            source_document_version_id=version.id,
        ),
    ]
    audit(
        db,
        correlation_id=payload.correlation_id,
        event_type="G10_BRIDGE_PACKAGE_ACCEPTED",
        entity_type="Phase4SourceChangeEvent",
        entity_id=event.id,
        actor_id=f"bridge:{identity.object_id}",
        after={"attempt_id": payload.attempt_id, "package_sha256": package_sha256, "verified_assertion_created": False, "projection_created": False},
    )
    return {
        "result": "ACCEPTED",
        "attempt_id": payload.attempt_id,
        "source_event_id": event.id,
        "evidence_envelope_id": evidence.id,
        "classification_envelope_id": classification.id,
        "document_version_id": version.id,
        "field_observation_id": observation.id,
        "candidate_assertion_ids": [candidate.id for candidate in candidates],
        "verified_assertion_created": False,
        "projection_created": False,
        "signature_verified": True,
        "package_sha256": package_sha256,
        "bridge_client_id": identity.client_id,
        "bridge_object_id": identity.object_id,
    }
