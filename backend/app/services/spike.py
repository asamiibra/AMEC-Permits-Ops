from datetime import datetime, timezone
from statistics import median
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..models import *
from .document_intelligence import RuleBasedDocumentClassifier, LocalSyntheticExtractor
from .week2_workflows import classify_version, extract_version


def run_spike(db: Session, run: ExtractionSpikeRun, correlation_id: str) -> ExtractionSpikeRun:
    if run.dataset_type == DatasetType.APPROVED_REAL_TEST: raise ValueError("Real document spike is gated and must be explicitly approved in TEST")
    run.status = "RUNNING"; run.started_at = datetime.now(timezone.utc)
    versions = db.scalars(select(DocumentVersion).order_by(DocumentVersion.source_filename)).all()
    run.document_count = min(len(versions), 20)
    class_correct = 0; times = []; manual = 0; corrected = 0; usability = {k.value: 0 for k in EvidenceUsability}; failures = {}
    field_stats: dict[str, dict[str, int]] = {}
    for version in versions[:20]:
        classification = db.scalar(select(DocumentClassification).where(DocumentClassification.document_version_id == version.id).order_by(DocumentClassification.created_at.desc())) or classify_version(db, version, correlation_id)
        observations = db.scalars(select(FieldObservation).where(FieldObservation.document_version_id == version.id)).all()
        if not observations: observations = extract_version(db, version, correlation_id)
        expected = version.document.document_type.value
        correct = classification.predicted_type == expected
        class_correct += int(correct)
        degraded = bool(version.metadata_json.get("poor_ocr"))
        manual += int(degraded); corrected += int(degraded)
        duration = 18 + (12 if degraded else 0); times.append(duration)
        evidence = EvidenceUsability.POOR if degraded else EvidenceUsability.GOOD; usability[evidence.value] += 1
        if degraded: failures["OCR_UNREADABLE"] = failures.get("OCR_UNREADABLE", 0) + 1
        if version.metadata_json.get("wrong_project"): failures["WRONG_DOCUMENT_CLASS"] = failures.get("WRONG_DOCUMENT_CLASS", 0) + 1
        db.add(SpikeDocumentResult(spike_run_id=run.id, document_version_id=version.id, expected_class=expected, predicted_class=classification.predicted_type, result="CORRECT" if correct else "INCORRECT", critical_fields_json={"observed": len(observations)}, corrections=1 if degraded else 0, verification_time_seconds=duration, evidence_usability=evidence, failure_mode="OCR_UNREADABLE" if degraded else None))
        gold = db.scalars(select(GoldFieldLabel).where(GoldFieldLabel.document_version_id == version.id)).all()
        for label in gold:
            stats = field_stats.setdefault(db.get(FieldDefinition, label.field_definition_id).field_code, {"samples":0,"correct_candidate":0,"wrong_candidate":0,"missing_candidate":0,"keyed":0,"corrected":0}); stats["samples"] += 1
            candidate = next((o for o in observations if o.field_definition_id == label.field_definition_id), None)
            if not candidate: stats["missing_candidate"] += 1
            elif candidate.normalized_candidate_value == str(label.expected_semantic_value.get("value")): stats["correct_candidate"] += 1
            else: stats["wrong_candidate"] += 1
            stats["keyed"] += int(degraded); stats["corrected"] += int(degraded)
    for code, stats in field_stats.items(): db.add(SpikeFieldResult(spike_run_id=run.id, field_code=code, **stats))
    run.metrics_json = {"classification_agreement": class_correct / run.document_count if run.document_count else 0, "critical_candidate_agreement": sum(s["correct_candidate"] for s in field_stats.values()) / sum(s["samples"] for s in field_stats.values()) if field_stats else 0, "critical_wrong_candidates": sum(s["wrong_candidate"] for s in field_stats.values()), "manual_keyed_percentage": manual / run.document_count if run.document_count else 0, "human_correction_percentage": corrected / run.document_count if run.document_count else 0, "median_verification_time_seconds": median(times) if times else 0, "evidence_usability": usability, "failure_modes": failures, "automation_quality_note": "Candidate extraction metrics only; not final verified-value correctness.", "final_control_quality": "All synthetic candidates remain subject to verification; no auto-verified critical assertions."}
    run.status = "COMPLETED"; run.completed_at = datetime.now(timezone.utc)
    db.flush(); return run
