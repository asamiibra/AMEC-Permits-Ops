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
    ProposalSourceScan,
    ProposalSourceScanEntry,
)
from ..schemas.bridge_intake import BridgePackageIn, BridgeScanIn
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
from ..storage import DocumentStorageService, StorageTarget, create_binary_store
from ..storage.proposal_source_tree import LOGICAL_ROOT, LIVE_SOURCE_URI_PREFIX, _parts, classify_project_folder
from .proposal_source_workspace import canonical_source_project_identity, source_processing_state


MAX_DEFAULT_PAYLOAD_BYTES = 1_048_576


def _live_source_metadata(payload: BridgePackageIn) -> dict[str, Any]:
    """Validate and normalize a live Synology URI into source-tree metadata."""
    if not payload.source_path_snapshot.startswith(LIVE_SOURCE_URI_PREFIX):
        return {}
    logical = payload.source_path_snapshot.removeprefix(LIVE_SOURCE_URI_PREFIX)
    prefix = LOGICAL_ROOT + "/"
    if not logical.startswith(prefix):
        raise _error(403, "BRIDGE_SOURCE_PATH_NOT_ALLOWLISTED")
    relative = logical.removeprefix(prefix)
    parts = _parts(relative)
    if len(parts) < 2 or classify_project_folder(parts[0]) is None:
        raise _error(422, "BRIDGE_SOURCE_PROJECT_PATH_INVALID")
    if payload.source_filename != parts[-1]:
        raise _error(422, "BRIDGE_SOURCE_FILENAME_MISMATCH")
    return {
        "source_root": LOGICAL_ROOT,
        "source_project_number": classify_project_folder(parts[0]).number,
        "source_project_folder": parts[0],
        "source_relative_path": relative,
        "source_is_directory": False,
    }


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
        "scan_id": payload.scan_id,
        "scan_status": payload.scan_status,
        "scan_source_root": payload.scan_source_root,
        "scan_project_identity": payload.scan_project_identity,
        "scan_entry_type": payload.scan_entry_type,
        "scan_entry_size_bytes": payload.scan_entry_size_bytes,
        "scan_entry_mtime_token": payload.scan_entry_mtime_token,
        "scan_capture_status": payload.scan_capture_status,
        "scan_failure_reason": payload.scan_failure_reason,
        "scan_manifest_hash": payload.scan_manifest_hash,
        "scan_counts": payload.scan_counts,
    }).encode("utf-8")


def canonical_scan_signature_payload(payload: BridgeScanIn) -> bytes:
    return _json({
        "scan_id": payload.scan_id, "source_identity": payload.source_identity,
        "source_root": payload.source_root, "source_project_identity": payload.source_project_identity,
        "project_number": payload.project_number, "status": payload.status,
        "started_at": payload.started_at, "completed_at": payload.completed_at,
        "entries": [entry.model_dump(mode="json") for entry in payload.entries],
        "counts": payload.counts, "manifest_hash": payload.manifest_hash,
    }).encode("utf-8")


def ingest_bridge_scan(db: Session, payload: BridgeScanIn, identity: BridgeIdentity, settings) -> dict[str, Any]:
    """Persist a signed source enumeration before/independently of payloads."""
    allowed = {value.strip() for value in str(getattr(settings, "bridge_allowed_source_identities", "")).split(",") if value.strip()}
    if payload.source_identity not in allowed:
        raise _error(403, "BRIDGE_SOURCE_NOT_ALLOWLISTED")
    prefixes = tuple(value.strip() for value in str(getattr(settings, "bridge_allowed_source_path_prefixes", "")).split(",") if value.strip())
    if not any(payload.source_root.startswith(prefix) or payload.source_root == LOGICAL_ROOT for prefix in prefixes):
        raise _error(403, "BRIDGE_SOURCE_PATH_NOT_ALLOWLISTED")
    # Verify the manifest hash over stable entry identity, then the machine
    # signature over the exact scan envelope.
    canonical_entries = [entry.model_dump(mode="json") for entry in payload.entries]
    observed_hash = hashlib.sha256(_json(sorted(canonical_entries, key=lambda item: item["relative_path"])).encode()).hexdigest()
    if observed_hash != payload.manifest_hash:
        raise _error(422, "BRIDGE_SCAN_MANIFEST_HASH_MISMATCH")
    public_key_b64 = str(getattr(settings, "bridge_package_signing_public_key", "")).strip()
    if not public_key_b64:
        raise _error(503, "BRIDGE_SIGNING_KEY_NOT_CONFIGURED")
    try:
        public_key = Ed25519PublicKey.from_public_bytes(base64.b64decode(public_key_b64, validate=True))
        public_key.verify(base64.b64decode(payload.signature_b64, validate=True), canonical_scan_signature_payload(payload))
    except (ValueError, binascii.Error, InvalidSignature) as exc:
        raise _error(422, "BRIDGE_SIGNATURE_INVALID") from exc
    try:
        started = datetime.fromisoformat(payload.started_at.replace("Z", "+00:00"))
        completed = datetime.fromisoformat(payload.completed_at.replace("Z", "+00:00")) if payload.completed_at else None
    except ValueError as exc:
        raise _error(422, "BRIDGE_SCAN_TIMESTAMP_INVALID") from exc
    existing = db.scalar(select(ProposalSourceScan).where(ProposalSourceScan.source_identity == payload.source_identity, ProposalSourceScan.scan_id == payload.scan_id))
    if existing is not None:
        # Package envelopes create an IN_PROGRESS scan before the final
        # signed enumeration arrives.  Finalization is allowed to replace
        # that provisional hash and reconcile its entries; a terminal scan
        # with a different hash is still an idempotency violation.
        if existing.status in {"COMPLETED", "INCOMPLETE", "FAILED"} and existing.signed_manifest_hash != payload.manifest_hash:
            raise _error(409, "BRIDGE_SCAN_ID_REUSE_MISMATCH")
        existing.source_root = payload.source_root
        existing.source_project_identity = payload.source_project_identity
        existing.project_number = payload.project_number
        existing.status = payload.status
        existing.started_at = started
        existing.completed_at = completed
        existing.signed_manifest_hash = payload.manifest_hash
        existing.signature_b64 = payload.signature_b64
        existing.metadata_json = {**(existing.metadata_json or {}), "signature_verified": True}
        for key in ("directories_seen", "files_seen", "total_bytes_seen", "files_successfully_captured", "files_skipped_oversize", "files_failed", "files_unsupported", "projects_unmapped"):
            if key in payload.counts:
                setattr(existing, key, int(payload.counts[key]))
        existing_entries = {row.relative_path: row for row in db.scalars(select(ProposalSourceScanEntry).where(ProposalSourceScanEntry.scan_id == existing.id)).all()}
        for entry in payload.entries:
            row = existing_entries.get(entry.relative_path)
            values = {"entry_type": entry.entry_type, "size_bytes": entry.size_bytes, "mtime_token": entry.mtime_token, "sha256": entry.sha256, "capture_status": entry.capture_status, "failure_reason": entry.failure_reason, "source_version_token": entry.source_version_token}
            if row is None:
                db.add(ProposalSourceScanEntry(scan_id=existing.id, relative_path=entry.relative_path, **values))
            else:
                for key, value in values.items():
                    setattr(row, key, value)
        db.flush()
        return {"result": "FINALIZED" if existing.status in {"COMPLETED", "INCOMPLETE", "FAILED"} else "IDEMPOTENT", "scan_id": existing.scan_id, "status": existing.status, "entry_count": len(payload.entries), "signature_verified": True}
    scan = ProposalSourceScan(scan_id=payload.scan_id, source_identity=payload.source_identity, source_root=payload.source_root, source_project_identity=payload.source_project_identity, project_number=payload.project_number, status=payload.status, started_at=started, completed_at=completed, bridge_machine_identity=identity.object_id, signed_manifest_hash=payload.manifest_hash, signature_b64=payload.signature_b64, metadata_json={"signature_verified": True})
    for key in ("directories_seen", "files_seen", "total_bytes_seen", "files_successfully_captured", "files_skipped_oversize", "files_failed", "files_unsupported", "projects_unmapped"):
        if key in payload.counts:
            setattr(scan, key, int(payload.counts[key]))
    db.add(scan)
    db.flush()
    for entry in payload.entries:
        db.add(ProposalSourceScanEntry(scan_id=scan.id, relative_path=entry.relative_path, entry_type=entry.entry_type, size_bytes=entry.size_bytes, mtime_token=entry.mtime_token, sha256=entry.sha256, capture_status=entry.capture_status, failure_reason=entry.failure_reason, source_version_token=entry.source_version_token))
    db.flush()
    return {"result": "RECORDED", "scan_id": scan.scan_id, "status": scan.status, "entry_count": len(payload.entries), "signature_verified": True}


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


def _record_scan_entry(db: Session, payload: BridgePackageIn, identity: BridgeIdentity, live_metadata: dict[str, Any], package_sha256: str) -> ProposalSourceScan | None:
    """Persist scan enumeration independently from payload arrival."""
    if not payload.scan_id:
        return None
    project_folder = str(live_metadata.get("source_project_folder") or "")
    project_number = str(live_metadata.get("source_project_number") or payload.project_id)
    source_project_identity = payload.scan_project_identity or canonical_source_project_identity(number=int(project_number) if project_number.isdigit() else 0, folder_name=project_folder or project_number, logical_root=payload.scan_source_root or LOGICAL_ROOT, source_system=payload.source_identity)
    scan = db.scalar(select(ProposalSourceScan).where(ProposalSourceScan.source_identity == payload.source_identity, ProposalSourceScan.scan_id == payload.scan_id))
    now = datetime.now(timezone.utc)
    if scan is None:
        scan = ProposalSourceScan(scan_id=payload.scan_id, source_identity=payload.source_identity, source_root=payload.scan_source_root or LOGICAL_ROOT, source_project_identity=source_project_identity, project_number=project_number, status="IN_PROGRESS", started_at=now, bridge_machine_identity=identity.object_id, signed_manifest_hash=payload.scan_manifest_hash, signature_b64=payload.signature_b64)
        db.add(scan)
        db.flush()
    entry_path = str(live_metadata.get("source_relative_path") or payload.source_path_snapshot)
    entry = db.scalar(select(ProposalSourceScanEntry).where(ProposalSourceScanEntry.scan_id == scan.id, ProposalSourceScanEntry.relative_path == entry_path))
    entry_values = {"entry_type": payload.scan_entry_type, "size_bytes": int(payload.scan_entry_size_bytes if payload.scan_entry_size_bytes is not None else payload.size_bytes), "mtime_token": payload.scan_entry_mtime_token or payload.mtime_utc, "sha256": package_sha256 if payload.scan_entry_type == "FILE" else None, "capture_status": payload.scan_capture_status or ("CAPTURED" if payload.scan_entry_type == "FILE" else "PRESENT"), "failure_reason": payload.scan_failure_reason, "source_version_token": payload.source_version_token}
    if entry is None:
        entry = ProposalSourceScanEntry(scan_id=scan.id, relative_path=entry_path, **entry_values)
        db.add(entry)
    else:
        for key, value in entry_values.items():
            setattr(entry, key, value)
    if payload.scan_counts:
        for key in ("directories_seen", "files_seen", "total_bytes_seen", "files_successfully_captured", "files_skipped_oversize", "files_failed", "files_unsupported", "projects_unmapped"):
            if key in payload.scan_counts:
                setattr(scan, key, int(payload.scan_counts[key]))
    if payload.scan_status:
        scan.status = payload.scan_status
        if payload.scan_status in {"COMPLETED", "INCOMPLETE", "FAILED"}:
            scan.completed_at = now
    return scan


def ingest_bridge_package(db: Session, payload: BridgePackageIn, identity: BridgeIdentity, settings) -> dict[str, Any]:
    raw, package_sha256 = _decode_payload(payload, settings)
    _validate_package(payload, raw, settings)
    live_metadata = _live_source_metadata(payload)
    scan = _record_scan_entry(db, payload, identity, live_metadata, package_sha256)
    synthetic_fixture = payload.source_identity == "QATAR_SYNOLOGY_SYNTHETIC_FIXTURE" or payload.source_path_snapshot.startswith("synthetic://")
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
    source_metadata = {
        "bridge_attempt_id": payload.attempt_id,
        "source_identity": payload.source_identity,
        "source_path_snapshot": payload.source_path_snapshot,
        "source_version_token": payload.source_version_token,
        "source_mtime_utc": payload.mtime_utc,
        "source_presence_state": "PRESENT",
        "processing_state": source_processing_state(payload.source_filename, payload.mime_type),
        "synthetic_non_business_fixture": synthetic_fixture,
        **live_metadata,
    }
    if synthetic_fixture:
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
            metadata_json=source_metadata,
            synthetic_content=raw,
        )
        db.add(version)
        db.flush()
        document.current_version_id = version.id
    else:
        # Live bytes are published through the canonical managed store before
        # the source version is made current. The Azure API never reaches SMB.
        try:
            store = create_binary_store()
            config = getattr(store, "config", None)
            share_id = getattr(config, "container", None) or getattr(config, "share", None) or "managed-artifacts"
            stored = DocumentStorageService(store).store_version(
                db,
                document=document,
                content=raw,
                filename=payload.source_filename,
                mime_type=payload.mime_type,
                target=StorageTarget(store.provider_id, share_id, f"proposal-sources/{payload.project_id}"),
                # AuditEvent.actor_id is a UUID-sized column.  Keep the
                # authenticated machine object id as the actor identity and
                # carry the bridge context in the event type/metadata.
                actor=identity.object_id,
                correlation_id=payload.correlation_id,
                idempotency_key=f"bridge-source:{payload.source_path_snapshot}:{package_sha256}",
                source_system="QATAR_SOURCE_INTAKE_BRIDGE",
                metadata=source_metadata,
                version_number=1,
            )
            version = stored.version
        except Exception as exc:
            # Preserve the fail-closed public error while making the runtime
            # diagnosis actionable without exposing connection strings,
            # source bytes, or other secret-bearing exception text.
            storage_code = getattr(getattr(exc, "code", None), "value", None) or type(exc).__name__
            raise _error(503, "BRIDGE_CANONICAL_STORAGE_FAILED", storage_error_class=storage_code) from exc

    event = Phase4SourceChangeEvent(
        event_id=event_id,
        scan_id_or_observation_group=f"{payload.scan_id or 'bridge-scan'}:{payload.attempt_id}",
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
        handler_parser_identity="g10-synthetic-bridge-package-v1" if synthetic_fixture else "qatar-live-bridge-package-v1",
        metering_json={"external_calls": 0, "bytes_read": len(raw), "real_content": not synthetic_fixture},
        warnings_json=["SYNTHETIC_NON_BUSINESS_FIXTURE"] if synthetic_fixture else [],
        content_retention_class="SYNTHETIC_FIXTURE_BYTES" if synthetic_fixture else "CANONICAL_MANAGED_STORAGE",
        evidence_json={
            "attempt_id": payload.attempt_id,
            "document_version_id": version.id,
            "package_sha256": package_sha256,
            "source_identity": payload.source_identity,
            "source_path_snapshot": payload.source_path_snapshot,
            "size_bytes": len(raw),
            "mtime_utc": payload.mtime_utc,
            "signature_verified": True,
            **live_metadata,
        },
    )
    db.add(evidence)
    db.flush()

    classifier_payload = ClassifierV2Request(
        fixture_id=f"g10-bridge:{payload.attempt_id}" if synthetic_fixture else f"qatar-live-bridge:{payload.attempt_id}",
        source_artifact_id=payload.source_path_snapshot,
        source_version_token=payload.source_version_token,
        source_mode=payload.source_mode,
        scope_type=payload.scope_type,
        scope_id=payload.scope_id,
        correlation_id=payload.correlation_id,
        evidence_ids=[f"synthetic-evidence://g10-bridge/{payload.attempt_id}" if synthetic_fixture else f"bridge-evidence://qatar-live/{payload.attempt_id}"],
        document_type_hint="CONTROLLED_SYNTHETIC_DOCUMENT" if synthetic_fixture else "SOURCE_DOCUMENT",
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
        actor_id=identity.object_id,
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
