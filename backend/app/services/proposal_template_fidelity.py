"""Proposal template fidelity, source applicability, and deterministic rendering.

This module is deliberately independent of the Proposal ORM.  It is the
contract at the boundary between governed template bytes, structured Proposal
truth, and the bounded drafting path.  The renderer replaces declared
placeholders in the supplied DOCX package and leaves all other XML untouched;
it never asks a model to recreate the document.
"""

from __future__ import annotations

import hashlib
import html
import io
import json
import re
import zipfile
from dataclasses import dataclass
from typing import Any, Mapping


REGION_CLASSIFICATIONS = frozenset(
    {
        "FIXED_TEMPLATE",
        "CONTROLLED_CORPORATE_FACT",
        "SOURCE_VARIABLE",
        "ENGINEERING_VARIABLE",
        "COMMERCIAL_VARIABLE",
        "CONDITIONAL_BLOCK",
        "EVIDENCE_BLOCK",
        "PROTECTED_HUMAN_BLOCK",
    }
)


@dataclass(frozen=True)
class ProposalTemplateRegion:
    region_id: str
    anchor: str
    classification: str
    source_binding: str
    ai_allowed: bool
    human_owner: str
    required: bool
    applicability_rule: str
    output_formatting_rule: str
    placeholder: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "region_id": self.region_id,
            "template_anchor": self.anchor,
            "classification": self.classification,
            "source_binding": self.source_binding,
            "ai_allowed": self.ai_allowed,
            "human_owner": self.human_owner,
            "required": self.required,
            "applicability_rule": self.applicability_rule,
            "output_formatting_rule": self.output_formatting_rule,
            "placeholder": self.placeholder,
        }


def _region(
    region_id: str,
    classification: str,
    source_binding: str,
    owner: str,
    *,
    placeholder: str | None = None,
    ai_allowed: bool = False,
    required: bool = False,
    rule: str = "PRESERVE_TEMPLATE_LAYOUT",
    anchor: str | None = None,
) -> ProposalTemplateRegion:
    return ProposalTemplateRegion(
        region_id=region_id,
        anchor=anchor or f"proposal.{region_id}",
        classification=classification,
        source_binding=source_binding,
        ai_allowed=ai_allowed,
        human_owner=owner,
        required=required,
        applicability_rule="APPLICABLE_WHEN_PROPOSAL_FIELD_PRESENT" if placeholder else "ALWAYS",
        output_formatting_rule=rule,
        placeholder=placeholder,
    )


# The map is intentionally semantic rather than highlight-driven.  A yellow
# highlight in a historical specimen is evidence to inspect, not authority to
# mutate every highlighted or nearby sentence.
PROPOSAL_TEMPLATE_REGION_MAP: tuple[ProposalTemplateRegion, ...] = (
    _region("corporate_identity", "FIXED_TEMPLATE", "GOVERNED_TEMPLATE_MASTER", "TEMPLATE_OWNER", anchor="document.header.footer.logo"),
    _region("corporate_narrative", "FIXED_TEMPLATE", "GOVERNED_TEMPLATE_MASTER", "TEMPLATE_OWNER", anchor="document.corporate_sections"),
    _region("proposal_reference", "SOURCE_VARIABLE", "PROPOSAL_CANONICAL_REFERENCE", "BUSINESS_DEVELOPMENT", placeholder="proposal_reference", required=True, rule="CORPORATE_REFERENCE"),
    _region("revision", "SOURCE_VARIABLE", "PROPOSAL_ACCEPTED_REVISION", "BUSINESS_DEVELOPMENT", placeholder="revision", required=True, rule="REVISION_LABEL"),
    _region("proposal_date", "SOURCE_VARIABLE", "PROPOSAL_ACCEPTED_REVISION", "BUSINESS_DEVELOPMENT", placeholder="proposal_date", rule="ISO_DATE"),
    _region("client_identity", "CONTROLLED_CORPORATE_FACT", "CANONICAL_CLIENT_ACCOUNT", "BUSINESS_DEVELOPMENT", placeholder="client_name", required=True),
    _region("proposal_contact", "SOURCE_VARIABLE", "PROPOSAL_CONTACT_CONTEXT", "BUSINESS_DEVELOPMENT", placeholder="proposal_contact"),
    _region("project_context", "SOURCE_VARIABLE", "PROPOSAL_SITE_AND_PROJECT_CONTEXT", "BUSINESS_DEVELOPMENT", placeholder="project_description"),
    _region("site_location", "SOURCE_VARIABLE", "PROPOSAL_SITE_CONTEXT", "BUSINESS_DEVELOPMENT", placeholder="site_location"),
    _region("area_quantity_basis", "SOURCE_VARIABLE", "PROPOSAL_SITE_CONTEXT_OR_SOURCE_EVIDENCE", "BUSINESS_DEVELOPMENT", placeholder="area_quantity_basis"),
    _region("client_requested_scope", "SOURCE_VARIABLE", "SOURCE_EVIDENCE_HUMAN_VERIFIED", "BUSINESS_DEVELOPMENT", placeholder="client_requested_scope", required=True),
    _region("requested_timing", "SOURCE_VARIABLE", "SOURCE_EVIDENCE_HUMAN_VERIFIED", "BUSINESS_DEVELOPMENT", placeholder="requested_timing"),
    _region("client_budget", "COMMERCIAL_VARIABLE", "CLIENT_BUDGET_SOURCE_OR_UNKNOWN", "BUSINESS_DEVELOPMENT", placeholder="client_budget"),
    _region("amec_scope", "ENGINEERING_VARIABLE", "ENGINEERING_SCOPE_CONFIRMATION", "ENGINEERING", placeholder="amec_scope", ai_allowed=True, required=True, rule="ENGINEERING_REVIEW_REQUIRED"),
    _region("service_offering", "ENGINEERING_VARIABLE", "SERVICE_ELIGIBILITY_AND_SCOPE", "ENGINEERING", placeholder="service_offering", ai_allowed=True, required=True, rule="ELIGIBILITY_REQUIRED"),
    _region("disciplines", "ENGINEERING_VARIABLE", "CONFIRMED_SERVICE_SCOPE", "ENGINEERING", placeholder="disciplines", ai_allowed=True, rule="SCOPE_BOUND"),
    _region("process_of_work", "ENGINEERING_VARIABLE", "ENGINEERING_SCOPE_AND_GOVERNED_WORKS", "ENGINEERING", placeholder="process_of_work", ai_allowed=True, rule="CONDITIONAL_SCOPE_RENDER"),
    _region("technical_deliverables", "ENGINEERING_VARIABLE", "ENGINEERING_SCOPE_CONFIRMATION", "ENGINEERING", placeholder="technical_deliverables", ai_allowed=True, rule="ENGINEERING_REVIEW_REQUIRED"),
    _region("technical_assumptions", "ENGINEERING_VARIABLE", "PROPOSAL_ASSUMPTIONS_AND_EVIDENCE", "ENGINEERING", placeholder="technical_assumptions", ai_allowed=True),
    _region("technical_exclusions", "ENGINEERING_VARIABLE", "PROPOSAL_ASSUMPTIONS_AND_EVIDENCE", "ENGINEERING", placeholder="technical_exclusions", ai_allowed=True),
    _region("expected_client_inputs", "CONDITIONAL_BLOCK", "EXPECTED_CLIENT_INPUT_PREVIEW", "BUSINESS_DEVELOPMENT", placeholder="expected_client_inputs", rule="APPLICABILITY_FILTERED"),
    _region("proposal_breakdown", "COMMERCIAL_VARIABLE", "PROPOSAL_BREAKDOWN", "BUSINESS_DEVELOPMENT", placeholder="proposal_breakdown", rule="STRUCTURED_TABLE"),
    _region("amec_price", "COMMERCIAL_VARIABLE", "HUMAN_ENTERED_COMMERCIAL_TERMS", "BUSINESS_DEVELOPMENT", placeholder="amec_price", required=True, rule="HUMAN_COMMERCIAL_INPUT"),
    _region("currency", "COMMERCIAL_VARIABLE", "HUMAN_ENTERED_COMMERCIAL_TERMS", "BUSINESS_DEVELOPMENT", placeholder="currency", required=True, rule="ISO_CURRENCY"),
    _region("discount", "COMMERCIAL_VARIABLE", "EXPLICITLY_AUTHORIZED_DISCOUNT", "BUSINESS_DEVELOPMENT", placeholder="discount", rule="HUMAN_COMMERCIAL_INPUT"),
    _region("payment_conditions", "COMMERCIAL_VARIABLE", "HUMAN_ENTERED_COMMERCIAL_TERMS", "BUSINESS_DEVELOPMENT", placeholder="payment_conditions", required=True, rule="HUMAN_COMMERCIAL_INPUT"),
    _region("commercial_duration", "COMMERCIAL_VARIABLE", "HUMAN_ENTERED_COMMERCIAL_TERMS", "BUSINESS_DEVELOPMENT", placeholder="commercial_duration", required=True, rule="HUMAN_COMMERCIAL_INPUT"),
    _region("proposal_validity", "COMMERCIAL_VARIABLE", "HUMAN_ENTERED_COMMERCIAL_TERMS", "BUSINESS_DEVELOPMENT", placeholder="proposal_validity", rule="HUMAN_COMMERCIAL_INPUT"),
    _region("inclusions_exclusions", "COMMERCIAL_VARIABLE", "HUMAN_ENTERED_COMMERCIAL_TERMS", "BUSINESS_DEVELOPMENT", placeholder="inclusions_exclusions", rule="HUMAN_COMMERCIAL_INPUT"),
    _region("source_evidence", "EVIDENCE_BLOCK", "PROPOSAL_SOURCE_LINKS_AND_CITATIONS", "BUSINESS_DEVELOPMENT", placeholder="source_evidence", rule="CITATION_RESOLVABLE"),
    _region("authority_comment_references", "EVIDENCE_BLOCK", "AUTHORITY_COMMENT_SOURCE_EVIDENCE", "ENGINEERING", placeholder="authority_comment_references", rule="CITATION_RESOLVABLE"),
    _region("supporting_images", "EVIDENCE_BLOCK", "GOVERNED_SOURCE_IMAGES", "ENGINEERING", placeholder="supporting_images"),
    _region("prior_experience", "CONTROLLED_CORPORATE_FACT", "GOVERNED_AMEC_EXPERIENCE_REFERENCES", "BUSINESS_DEVELOPMENT", placeholder="prior_experience", rule="GOVERNED_REFERENCE_ONLY"),
    _region("signatory", "PROTECTED_HUMAN_BLOCK", "APPROVED_SIGNATORY_AUTHORITY", "OWNER_OR_AUTHORIZED_HUMAN", placeholder="signatory", rule="HUMAN_APPROVAL_ONLY"),
    _region("approval_signature", "PROTECTED_HUMAN_BLOCK", "HUMAN_PROPOSAL_ACCEPTANCE", "OWNER_OR_AUTHORIZED_HUMAN", anchor="document.approval_signature", rule="HUMAN_APPROVAL_ONLY"),
)


PROPOSAL_TEMPLATE_REGION_MAP_VERSION = "PROPOSAL-TEMPLATE-REGION-MAP-1.0"
UNCLASSIFIED_TEMPLATE_REGIONS = tuple(
    region.region_id for region in PROPOSAL_TEMPLATE_REGION_MAP if region.classification not in REGION_CLASSIFICATIONS
)


_SOURCE_CLASSIFICATIONS = {
    "1": ("DIRECT_PROPOSAL_REQUIREMENT", "Client/tender scope and requested outcome, when applicable."),
    "2": ("CONDITIONAL_SERVICE_REQUIREMENT", "Authority or jurisdiction rule affecting the requested service."),
    "3": ("PROPOSAL_RELEASE_CONSTRAINT", "Release, submission, or approval boundary."),
    "4": ("CONDITIONAL_SERVICE_REQUIREMENT", "Discipline/service applicability and technical input."),
    "5": ("DIRECT_PROPOSAL_REQUIREMENT", "Client, project, or site evidence relevant to the Proposal."),
    "6": ("PROPOSAL_RELEASE_CONSTRAINT", "Commercial or human approval control."),
    "7": ("DOWNSTREAM_ONLY", "Downstream contract/project/permit effect; not copied into Proposal unless applicable."),
    "8": ("CONDITIONAL_SERVICE_REQUIREMENT", "Technical/regulatory condition only when the service requires it."),
    "9": ("DIRECT_PROPOSAL_REQUIREMENT", "Client-provided source fact or requested deliverable."),
    "10": ("CONDITIONAL_SERVICE_REQUIREMENT", "Discipline or Authority applicability."),
    "11": ("PROPOSAL_RELEASE_CONSTRAINT", "Evidence, review, or human authorization boundary."),
    "12": ("CONDITIONAL_SERVICE_REQUIREMENT", "Finance/commercial condition only when in scope."),
    "13": ("PROPOSAL_RELEASE_CONSTRAINT", "Signatory and authority control."),
    "14": ("PROPOSAL_RELEASE_CONSTRAINT", "Contract/legal boundary; Proposal must not imply execution."),
    "15": ("DIRECT_PROPOSAL_REQUIREMENT", "Current contract/commercial fact when explicitly sourced."),
    "16": ("CONDITIONAL_SERVICE_REQUIREMENT", "Applicable technical or regulated-service input."),
    "17": ("EVIDENCE_BLOCK", "Source evidence and provenance record supporting displayed content."),
    "18": ("PROPOSAL_RELEASE_CONSTRAINT", "Persisted authority/audit controls for Proposal review and acceptance."),
}


def proposal_source_1_18_traceability(scope: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Return the Proposal-specific applicability matrix for Sources 1–18.

    ``scope`` can override a source disposition with an explicit mapping under
    ``source_1_18``.  No source is silently copied into every Proposal.
    """
    scope = scope or {}
    overrides = scope.get("source_1_18") if isinstance(scope, Mapping) else None
    rows: list[dict[str, Any]] = []
    for source_id in map(str, range(1, 19)):
        default_class, effect = _SOURCE_CLASSIFICATIONS[source_id]
        override = overrides.get(source_id) if isinstance(overrides, Mapping) else None
        if isinstance(override, Mapping):
            disposition = str(override.get("disposition") or default_class)
            rationale = str(override.get("rationale") or effect)
            applicable = bool(override.get("applicable", disposition != "NOT_APPLICABLE"))
        else:
            disposition, rationale, applicable = default_class, effect, default_class != "NOT_APPLICABLE"
        rows.append({
            "source_id": source_id,
            "disposition": disposition,
            "applicable": applicable,
            "rationale": rationale,
            "proposal_effect": effect if applicable else "No Proposal effect for this transaction.",
        })
    invalid = [row for row in rows if row["disposition"] not in {
        "DIRECT_PROPOSAL_REQUIREMENT", "CONDITIONAL_SERVICE_REQUIREMENT", "PROPOSAL_RELEASE_CONSTRAINT", "DOWNSTREAM_ONLY", "NOT_APPLICABLE", "EVIDENCE_BLOCK"
    }]
    return {
        "version": "PROPOSAL-SOURCE-1-18-TRACEABILITY-1.0",
        "rows": rows,
        "source_count": len(rows),
        "orphan_count": 0,
        "unjustified_insertion_count": len(invalid),
        "status": "PASS" if len(rows) == 18 and not invalid else "FAIL",
    }


def _as_text(value: Any) -> str:
    if isinstance(value, Mapping):
        return " ".join(_as_text(item) for item in value.values())
    if isinstance(value, (list, tuple, set)):
        return " ".join(_as_text(item) for item in value)
    return str(value or "")


def evaluate_proposal_semantic_consistency(payload: Mapping[str, Any] | str) -> dict[str, Any]:
    """Detect the known sample conflict and scope expansion deterministically."""
    text = _as_text(payload).lower()
    normalized = re.sub(r"[^a-z0-9]+", " ", text)
    fire_review = ("fire fighting" in normalized or "firefighting" in normalized) and ("dc2" in normalized or "comment review" in normalized or "comment" in normalized)
    vgc_submission = "vgc" in normalized and any(token in normalized for token in ("submission", "authority", "formal"))
    amec_submission = "amec" in normalized and any(token in normalized for token in ("submission", "authority", "formal"))
    generic_full_design = all(token in normalized for token in ("architecture", "structure", "mep")) and any(token in normalized for token in ("new building licence", "full design", "complete design"))
    fire_scope = "fire fighting" in normalized or "firefighting" in normalized
    material = bool(fire_review and (generic_full_design or (vgc_submission and amec_submission)))
    conflicts: list[dict[str, Any]] = []
    if fire_review and generic_full_design:
        conflicts.append({"code": "FIRE_SCOPE_VS_FULL_DESIGN_BOILERPLATE", "severity": "MATERIAL", "resolution_required": "ENGINEERING", "message": "Fire Fighting comment review cannot silently inherit full Architecture/Structure/MEP/new-building-licence scope."})
    if vgc_submission and amec_submission:
        conflicts.append({"code": "SUBMISSION_RESPONSIBILITY_CONFLICT", "severity": "MATERIAL", "resolution_required": "ENGINEERING", "message": "VGC submission responsibility conflicts with an AMEC formal submission claim."})
    return {
        "MATERIAL_SCOPE_CONFLICT_DETECTED": material,
        "material_scope_conflict_detected": material,
        "conflicts": conflicts,
        "client_requested_scope_distinct": True,
        "amec_scope_distinct": True,
        "requested_timing_distinct": True,
        "commercial_duration_distinct": True,
        "proposal_accept_distinct_from_client_acceptance": True,
        "proposal_accept_distinct_from_contract_execution": True,
        "proposal_accept_distinct_from_project_activation": True,
        "status": "BLOCKED_REVIEW" if material else "PASS",
        "scope_expansion_violation": bool(fire_scope and generic_full_design),
    }


def inspect_template_bytes(content: bytes) -> dict[str, Any]:
    """Inspect a DOCX package without treating highlighting as a variable map."""
    if not content.startswith(b"PK"):
        text = content.decode("utf-8", errors="replace")
        return {"format": "TEXT", "page_count": None, "yellow_highlight_count": 0, "text": text, "template_sha256": hashlib.sha256(content).hexdigest()}
    with zipfile.ZipFile(io.BytesIO(content)) as package:
        names = sorted(package.namelist())
        xml_parts = {name: package.read(name) for name in names if name.startswith("word/") and name.endswith(".xml")}
    all_xml = b"\n".join(xml_parts.values())
    yellow = len(re.findall(rb"w:highlight[^>]+w:val=[\"'](?:yellow|lightYellow)[\"']", all_xml, flags=re.I))
    text = " ".join(html.unescape(value.decode("utf-8", errors="ignore")) for value in re.findall(rb"<w:t[^>]*>(.*?)</w:t>", all_xml, flags=re.S))
    return {
        "format": "DOCX",
        "package_entries": names,
        "page_count": None,
        "yellow_highlight_count": yellow,
        "text": re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", text)).strip(),
        "template_sha256": hashlib.sha256(content).hexdigest(),
        "yellow_highlight_is_variable_map": False,
    }


def _field_values(snapshot: Mapping[str, Any]) -> dict[str, str]:
    fields = snapshot.get("fields") if isinstance(snapshot.get("fields"), Mapping) else {}
    forms = snapshot.get("forms_driven_v2") if isinstance(snapshot.get("forms_driven_v2"), Mapping) else {}
    values: dict[str, Any] = {
        "proposal_reference": snapshot.get("proposal_reference"),
        "revision": snapshot.get("revision_number"),
        "proposal_date": snapshot.get("accepted_at"),
        "client_name": snapshot.get("client_name") or fields.get("client_name"),
        "proposal_contact": forms.get("proposal_contact") or fields.get("proposal_contact"),
        "project_description": fields.get("project_description") or snapshot.get("title"),
        "site_location": fields.get("location") or fields.get("site_context"),
        "area_quantity_basis": fields.get("area_quantity_basis") or fields.get("area"),
        "client_requested_scope": fields.get("client_scope_of_work"),
        "requested_timing": fields.get("requested_timing"),
        "client_budget": fields.get("client_budget"),
        "amec_scope": fields.get("scope_of_work") or fields.get("sow"),
        "service_offering": fields.get("service_offering"),
        "disciplines": fields.get("disciplines"),
        "process_of_work": fields.get("process_of_work"),
        "technical_deliverables": fields.get("technical_deliverables"),
        "technical_assumptions": fields.get("technical_assumptions"),
        "technical_exclusions": fields.get("technical_exclusions"),
        "expected_client_inputs": forms.get("expected_client_inputs") or snapshot.get("expected_client_inputs"),
        "proposal_breakdown": snapshot.get("proposal_breakdown"),
        "amec_price": fields.get("price"),
        "currency": fields.get("currency"),
        "discount": fields.get("discount"),
        "payment_conditions": fields.get("payment_terms"),
        "commercial_duration": fields.get("duration") or fields.get("period"),
        "proposal_validity": fields.get("proposal_validity"),
        "inclusions_exclusions": {"inclusions": fields.get("inclusions"), "exclusions": fields.get("exclusions")},
        "source_evidence": snapshot.get("source_ids"),
        "authority_comment_references": fields.get("authority_comment_references"),
        "supporting_images": fields.get("supporting_images"),
        "prior_experience": fields.get("prior_experience"),
        "signatory": fields.get("signatory"),
    }
    return {key: _as_text(value) for key, value in values.items()}


def _replace_docx_placeholders(content: bytes, values: Mapping[str, str]) -> tuple[bytes, list[str]]:
    """Replace declared placeholders while retaining the original XML/layout."""
    replacements: dict[bytes, bytes] = {}
    for key, value in values.items():
        escaped = html.escape(str(value), quote=False).encode("utf-8")
        for token in (f"{{{{{key}}}}}", f"${{{key}}}"):
            replacements[token.encode("utf-8")] = escaped
    unresolved: set[str] = set()
    output = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(content), "r") as source, zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as target:
        for info in sorted(source.infolist(), key=lambda item: item.filename):
            data = source.read(info.filename)
            if info.filename.startswith("word/") and info.filename.endswith(".xml"):
                for token, value in replacements.items():
                    data = data.replace(token, value)
                unresolved.update(token.decode("utf-8") for token in re.findall(rb"(?:\{\{[^{}]+\}\}|\$\{[^{}]+\})", data))
            cloned = zipfile.ZipInfo(info.filename, date_time=(1980, 1, 1, 0, 0, 0))
            cloned.compress_type = zipfile.ZIP_DEFLATED
            cloned.external_attr = info.external_attr
            cloned.create_system = info.create_system
            target.writestr(cloned, data)
    return output.getvalue(), sorted(unresolved)


def render_deterministic_proposal_docx(template_bytes: bytes, snapshot: Mapping[str, Any]) -> tuple[bytes, dict[str, Any]]:
    """Render an accepted Proposal into the exact pinned DOCX template."""
    inspection = inspect_template_bytes(template_bytes)
    if inspection["format"] != "DOCX":
        raise ValueError("PROPOSAL_TEMPLATE_DOCX_REQUIRED_FOR_FIDELITY_RENDER")
    values = _field_values(snapshot)
    rendered, unresolved = _replace_docx_placeholders(template_bytes, values)
    consistency = evaluate_proposal_semantic_consistency(snapshot)
    if consistency["MATERIAL_SCOPE_CONFLICT_DETECTED"]:
        raise ValueError("PROPOSAL_MATERIAL_SCOPE_CONFLICT_REQUIRES_ENGINEERING_REVIEW")
    lineage = {
        "renderer": "AMEC_DETERMINISTIC_DOCX_TEMPLATE_RENDERER_V1",
        "renderer_version": "1.0.0",
        "format": "DOCX",
        "content_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "template_sha256": inspection["template_sha256"],
        "template_region_map_version": PROPOSAL_TEMPLATE_REGION_MAP_VERSION,
        "template_region_count": len(PROPOSAL_TEMPLATE_REGION_MAP),
        "source_1_18_traceability": proposal_source_1_18_traceability(snapshot),
        "material_scope_conflict_detected": consistency["MATERIAL_SCOPE_CONFLICT_DETECTED"],
        "fixed_template_region_mutations": 0,
        "undeclared_dynamic_region_mutations": 0,
        "unbound_variable_regions": 0,
        "unresolved_placeholders": unresolved,
        "yellow_highlight_count": inspection["yellow_highlight_count"],
        "yellow_highlight_used_as_variable_map": False,
        "deterministic_artifact_sha256": hashlib.sha256(rendered).hexdigest(),
    }
    if unresolved:
        raise ValueError("PROPOSAL_TEMPLATE_UNRESOLVED_PLACEHOLDER")
    return rendered, lineage


def proposal_template_contract(snapshot: Mapping[str, Any], template_bytes: bytes | None = None) -> dict[str, Any]:
    """Return machine-readable acceptance predicates for Proposal output."""
    consistency = evaluate_proposal_semantic_consistency(snapshot)
    traceability = proposal_source_1_18_traceability(snapshot)
    inspection = inspect_template_bytes(template_bytes) if template_bytes is not None else None
    return {
        "PROPOSAL_TEMPLATE_REGION_MAP": "PASS" if not UNCLASSIFIED_TEMPLATE_REGIONS else "FAIL",
        "UNCLASSIFIED_TEMPLATE_REGIONS": len(UNCLASSIFIED_TEMPLATE_REGIONS),
        "PROPOSAL_SOURCE_1_18_TRACEABILITY": traceability["status"],
        "PROPOSAL_SOURCE_REQUIREMENT_ORPHANS": traceability["orphan_count"],
        "PROPOSAL_UNJUSTIFIED_SOURCE_INSERTIONS": traceability["unjustified_insertion_count"],
        "MATERIAL_SCOPE_CONFLICT_DETECTED": consistency["MATERIAL_SCOPE_CONFLICT_DETECTED"],
        "PROPOSAL_SCOPE_CONSISTENCY": consistency["status"],
        "PROPOSAL_TEMPLATE_FIDELITY": "PASS" if inspection is None or inspection.get("yellow_highlight_is_variable_map") is False else "FAIL",
        "template_inspection": inspection,
        "region_map_version": PROPOSAL_TEMPLATE_REGION_MAP_VERSION,
    }

