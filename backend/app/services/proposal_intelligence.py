"""Proposal-owned P08 Intelligence orchestration and review boundary."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, replace
from typing import Any
from uuid import uuid4

from sqlalchemy import select, true
from sqlalchemy.orm import Session, sessionmaker

from backend.app.ai.provider import AIProviderRequest, AIProviderResult, AIProviderUsage
from backend.app.ai.skill_registry import PROPOSAL_GENERATION_SKILLS, PROPOSAL_SKILLS, SkillDefinition
from backend.app.ai.skill_runtime import RuntimeDependencies, SkillExecutionRequest, SkillRuntime
from backend.app.api.dependencies import AuthenticatedPrincipal
from backend.app.config.settings import Settings
from backend.app.models import (
    AIWorkProduct, CandidateAssertion, ContextDependency, ContextSnapshot,
    IntelligenceCitation,
    IntelligenceReviewDecision, Opportunity, ProposalAcceptedRevision,
    ProposalIntelligenceReviewBinding, User, WorkflowTask, WorkflowTaskStatus,
    ProposalRevision, ProposalSourceLink,
)
from backend.app.services.backend_realignment import persona_for_role, require_capability
from backend.app.services.intelligence_contracts import IntelligenceContractError, stable_hash
from backend.app.services.intelligence_foundation import (
    dependency_current, promote_verified_assertion_from_decision,
    register_eval_pack, record_module_review_decision, revalidate_snapshot, invalidate_dependency,
)


P08_POLICY_VERSION = "PROPOSAL_INTELLIGENCE_V1-1.0"
P08_REVIEW_CAPABILITY = "BD_PROPOSAL_INTELLIGENCE_REVIEW"
P08_EVAL_PACK_ID = "proposal-intelligence-v1"
P08_EVAL_PACK_VERSION = "1.0.0"
P08_CRITICAL_CASES = (
    "cross-project", "wrong-persona", "missing-capability", "stale-revision", "stale-document",
    "stale-verified-assertion", "stale-master-content", "stale-policy", "source-mismatch",
    "citation-mismatch", "malformed-output", "trust-floor", "sensitivity", "protected-action",
    "policy-spoof", "skill-spoof", "provider-spoof", "prompt-injection", "provider-failure",
    "context-race", "stale-review", "duplicate-review", "conflicting-review", "corrected-candidate",
    "analysis-not-truth", "unrelated-dependency-current",
)
P08_EVAL_PACK_HASH = stable_hash({"eval_pack_id": P08_EVAL_PACK_ID, "version": P08_EVAL_PACK_VERSION, "owning_module": "proposal", "critical_case_policy": "ALL_SECURITY_CURRENTNESS_AUTHORITY_CRITICAL", "acceptance_threshold_policy": "CRITICAL_100_PERCENT_NO_SKIPS"})
OPERATION_TO_SKILL = {
    "tender-intake-analysis": "proposal.tender-intake-analysis",
    "requirement-evidence-analysis": "proposal.requirement-evidence-analysis",
    "section-draft": "proposal.section-draft",
    "commercial-consistency-review": "proposal.commercial-consistency-review",
    "lpo-variance-analysis": "proposal.lpo-variance-analysis",
    "handoff-preflight": "proposal.handoff-preflight",
    "document-change-plan": "proposal.document-change-plan",
    "intake-analysis": "proposal.tender-intake-analysis",
    "scope-technical-analysis": "proposal.section-draft",
    "readiness-explanation": "proposal.handoff-preflight",
}
_SKILLS = {item.manifest.skill_id: item for item in (*PROPOSAL_SKILLS, *PROPOSAL_GENERATION_SKILLS)}
_REVIEW_PERSONA_BY_SKILL = {
    "proposal.tender-intake-analysis": "BUSINESS_DEVELOPMENT",
    "proposal.requirement-evidence-analysis": "BUSINESS_DEVELOPMENT",
    "proposal.section-draft": "ENGINEERING",
    "proposal.commercial-consistency-review": "BUSINESS_DEVELOPMENT",
    "proposal.lpo-variance-analysis": "BUSINESS_DEVELOPMENT",
    "proposal.handoff-preflight": "BUSINESS_DEVELOPMENT",
    "proposal.document-change-plan": "BUSINESS_DEVELOPMENT",
}


def _review_persona_for_work_product(work_product: AIWorkProduct) -> str:
    """Return the accountable module reviewer for this Proposal skill."""
    return _REVIEW_PERSONA_BY_SKILL.get(work_product.skill_id, "BUSINESS_DEVELOPMENT")


def _allowed_review_personas(binding: ProposalIntelligenceReviewBinding) -> set[str]:
    """Allow Owner override without widening the module review boundary."""
    return {"OWNER", "SYSTEM_ADMIN", binding.required_persona}


def _runtime_settings(settings: Settings, provider: Any | None) -> Settings:
    if not isinstance(provider, ProposalDeterministicProvider):
        return settings
    # Synthetic API/browser acceptance still traverses the shared D4 gateway,
    # but never contacts Azure. These fixed binding values make that boundary
    # explicit without weakening production settings validation.
    return settings.model_copy(update={
        "ai_feature_enabled": True,
        "ai_external_inference_enabled": True,
        "ai_d4_commissioning_id": "P08-SYNTHETIC-D4",
        "ai_azure_openai_endpoint": "https://p08-synthetic.openai.azure.com",
        "ai_uami_client_id": "00000000-0000-0000-0000-000000000001",
        "ai_uami_principal_id": "00000000-0000-0000-0000-000000000002",
        "ai_azure_tenant_id": "00000000-0000-0000-0000-000000000003",
        "ai_d3_project_ids": ("synthetic-proposal",),
        # The Proposal source workspace intentionally carries the complete
        # recursive source set (the pilot has 13 files).  The provider input
        # contains bounded projections for each source, so use the registered
        # Proposal skill budget rather than the smaller single-document
        # default.  This changes only the deterministic synthetic provider;
        # production settings and the real gateway remain unchanged.
        # The complete AMEC baseline is intentionally passed through the
        # governed synthetic context for this acceptance path.  Its editable
        # block projection can be larger than the ordinary single-document
        # bound; production Azure runs keep the commissioned bound and must
        # use the provider's document chunking path.
        "ai_max_input_token_upper_bound": 1_000_000,
        "ai_max_output_tokens": 512,
        "ai_max_requests_per_user_per_minute": 100,
        "ai_max_requests_per_user_per_hour": 1000,
        "ai_max_requests_per_project_per_hour": 1000,
        "ai_max_requests_global_per_hour": 10000,
        "ai_max_estimated_cost_usd_per_request": 1.0,
        "ai_max_estimated_cost_usd_per_day": 100.0,
        "ai_input_price_usd_per_1m_tokens": 1.0,
        "ai_output_price_usd_per_1m_tokens": 1.0,
        "ai_pricing_source_reference": "P08-SYNTHETIC-PRICING",
    })


def _accepted(db: Session, proposal_id: str) -> ProposalAcceptedRevision | None:
    return db.scalar(select(ProposalAcceptedRevision).where(
        ProposalAcceptedRevision.proposal_id == proposal_id,
        ProposalAcceptedRevision.status == "ACCEPTED",
    ).order_by(ProposalAcceptedRevision.revision_number.desc(), ProposalAcceptedRevision.accepted_at.desc()))


def _working(db: Session, proposal_id: str) -> ProposalRevision | None:
    return db.scalar(select(ProposalRevision).where(
        ProposalRevision.proposal_id == proposal_id,
        ProposalRevision.status == "DRAFT",
    ).order_by(ProposalRevision.revision_number.desc()))


def _current_revision_identity(
    proposal: Opportunity,
    accepted: ProposalAcceptedRevision | None,
    working: ProposalRevision | None,
    *,
    accepted_required: bool,
) -> str:
    selected_revision = accepted if accepted_required and accepted is not None else (working if working is not None else accepted)
    if selected_revision is not None:
        return f"{selected_revision.id}:{selected_revision.revision_number}:{selected_revision.content_hash}"
    return stable_hash({
        "proposal_id": proposal.id,
        "proposal_fields": proposal.proposal_fields_json,
        "updated_at": proposal.updated_at.isoformat(),
    })


def _proposal_sources(db: Session, context: ProposalContext) -> list[dict[str, Any]]:
    """Build the source set server-side from Proposal-owned bindings.

    The browser supplies only the requested skill.  Source links, evidence,
    and test Master Content are selected from governed records here.
    """
    sources: list[dict[str, Any]] = [{
        "key": "proposal-current-state",
        "context_type": "DOMAIN_ENTITY_REVISION",
        "selector": {"entity_type": "PROPOSAL", "entity_id": context.proposal.id},
    }]
    links = db.scalars(select(ProposalSourceLink).where(
        ProposalSourceLink.proposal_id == context.proposal.id,
        ProposalSourceLink.active == true(),
    ).order_by(ProposalSourceLink.created_at, ProposalSourceLink.id)).all()
    accepted_only = context.skill.manifest.skill_id in ACCEPTED_REVISION_SKILLS
    included_source_ids: set[str] | None = None
    # Proposal V1 source curation is persisted in the source manifest.  Use
    # that server-owned projection when selecting AI context so an Owner's
    # include/exclude decision survives refreshes and cannot be overridden by
    # a stale active link or browser state.
    try:
        from .proposal_source_workspace import build_effective_proposal_source_manifest
        workspace = (context.proposal.proposal_fields_json or {}).get("source_workspace") or {}
        if workspace.get("source_project_identity"):
            effective = build_effective_proposal_source_manifest(db, context.proposal, include_excluded=True)
            included_source_ids = {
                str(item.get("document_version_id"))
                for item in effective.get("entries", [])
                if item.get("included") and item.get("document_version_id")
            }
    except (KeyError, TypeError, ValueError):
        included_source_ids = None
    for index, link in enumerate(links, 1):
        role = link.source_role.upper()
        if accepted_only and role not in {"LPO_PO", "CLIENT_ACCEPTANCE", "CLIENT_RESPONSE", "DISTRIBUTION", "TENDER_DOCUMENT"}:
            continue
        if included_source_ids is not None and str(link.document_version_id) not in included_source_ids:
            continue
        sources.append({
            "key": f"proposal-source-{index}",
            "context_type": "DOCUMENT_VERSION",
            "selector": {"id": link.document_version_id},
            "required": role in {"TENDER", "TENDER_DOCUMENT", "LPO_PO"},
        })
    if context.skill.manifest.skill_id in {
        "proposal.requirement-evidence-analysis",
        "proposal.section-draft",
        "proposal.commercial-consistency-review",
    }:
        from .master_content import resolve_master_content_purpose
        resolution = resolve_master_content_purpose(db, module="BD", usage_type="PROPOSAL_TEMPLATE")
        if resolution["status"] == "RESOLVED":
            item = resolution["item"]
            sources.append({
                "key": "proposal-test-master-content",
                "context_type": "MASTER_CONTENT",
                "selector": {"master_content_item_id": item["id"], "document_version_id": item["version_id"], "content_type": item["content_type"]},
                "required": True,
            })
    return sources


ACCEPTED_REVISION_SKILLS = frozenset({
    "proposal.lpo-variance-analysis",
    "proposal.handoff-preflight",
})


def _revision_dependency(proposal: Opportunity, revision: ProposalAcceptedRevision) -> dict[str, Any]:
    return {
        "domain_entity": "PROPOSAL",
        "accepted_revision_id": revision.id,
        "accepted_revision_number": revision.revision_number,
        "accepted_revision_hash": revision.content_hash,
    }


def _principal(db: Session, principal: AuthenticatedPrincipal) -> AuthenticatedPrincipal:
    if not principal.user_id:
        user = db.scalar(select(User).where(User.active == true(), User.role == principal.role).order_by(User.id))
        if user is not None:
            return replace(principal, user_id=user.id, office_id=user.office_id)
    if not principal.user_id:
        raise IntelligenceContractError("INTELLIGENCE_REVIEW_AUTHENTICATED_PRINCIPAL_REQUIRED")
    return principal


def _skill(operation: str) -> SkillDefinition:
    try:
        return _SKILLS[OPERATION_TO_SKILL[operation]]
    except KeyError as exc:
        raise IntelligenceContractError("PROPOSAL_INTELLIGENCE_OPERATION_UNSUPPORTED") from exc


class ProposalDeterministicProvider:
    """Synthetic provider used only by the P08 test/runtime environment."""

    def execute_structured(self, request: AIProviderRequest) -> AIProviderResult:
        context = json.loads(request.provider_input).get("context", [])
        item = context[0] if context else {}
        projection = item.get("projection", {})
        citation = ["CIT-001"]
        name = request.schema_name
        if name in {"proposal_intake_analysis", "proposal_tender_intake_analysis"}:
            payload = {"summary": "Synthetic governed Proposal intake analysis.", "missing_information": [], "contradictions": [], "unresolved_candidate_facts": [], "source_currentness_issues": [], "citation_keys": citation}
        elif name == "proposal_requirement_evidence_analysis":
            payload = {"summary": "Synthetic requirement and evidence candidate map.", "requirement_candidates": [], "open_questions": [], "citation_keys": citation}
        elif name == "proposal_section_draft":
            payload = {"section_type": "Executive Summary", "draft_content": "Synthetic draft for human editing only.", "approved_content_used": [], "canonical_facts_used": [], "open_questions": [], "assumptions": [], "unsupported_claims": [], "citation_keys": citation, "draft_only": True}
        elif name == "proposal_commercial_consistency_review":
            payload = {"summary": "Synthetic commercial consistency review; disposition remains human-owned.", "variances": [], "open_questions": [], "citation_keys": citation}
        elif name == "proposal_lpo_variance_analysis":
            payload = {"summary": "Synthetic typed LPO comparison; no adjudication performed.", "accepted_revision_id": projection.get("accepted_revision_id", "unresolved"), "lpo_evidence_id": projection.get("lpo_evidence_id"), "differences": [], "citation_keys": citation}
        elif name == "proposal_document_change_plan":
            # The canonical Arabic technical-report DOCX is the only document
            # that may be mutated.  Other DOCX files remain source evidence;
            # they can never silently become a proposal baseline.
            from .proposal_technical_report_template import SECTION_KEYS, TEMPLATE_ID, TEMPLATE_VERSION
            documents = [
                entry for entry in context
                if entry.get("context_type") == "DOCUMENT_VERSION"
                and entry.get("projection", {}).get("editable_blocks")
            ]
            complete_documents = [
                entry for entry in documents
                if len(entry.get("projection", {}).get("editable_blocks") or []) >= 24
            ]
            baseline = next(
                (entry for entry in complete_documents
                 if (entry.get("projection", {}).get("template_id") == TEMPLATE_ID
                     or entry.get("projection", {}).get("template_baseline"))),
                None,
            )
            baseline_projection = baseline.get("projection", {}) if baseline else {}
            baseline_id = str(baseline_projection.get("document_version_id", "unresolved"))
            blocks = baseline_projection.get("editable_blocks", [])
            proposal_projection = next(
                (entry.get("projection") for entry in context
                 if entry.get("context_type") == "DOMAIN_ENTITY_REVISION"),
                {},
            ) or {}

            # Derive identity only from the server-owned Proposal projection or
            # the frozen Synology folder.  Do not use a historical DOCX as an
            # identity source, which is how Q-498 leaked into earlier drafts.
            project_number = str(
                proposal_projection.get("project_number")
                or proposal_projection.get("canonical_project_reference")
                or ""
            ).strip() or None
            project_name = str(proposal_projection.get("project_name") or "").strip() or None
            client_name = str(proposal_projection.get("client_name") or "").strip() or None
            for entry in context:
                projection = entry.get("projection") or {}
                path = str(projection.get("source_relative_path") or "")
                match = re.match(r"^\s*(\d{1,9})\s*[-–—]\s*(.+?)(?:/|$)", path)
                if match:
                    project_number = project_number or match.group(1)
                    project_name = project_name or match.group(2).strip()
            project_name = re.sub(r"^\s*\d{1,9}\s*[-–—:]\s*", "", project_name or "").strip() or "Needs Owner Review"
            client_name = re.sub(r"^\s*\d{1,9}\s*[-–—:]\s*", "", client_name or "").strip() or project_name
            if client_name.casefold().startswith("project "):
                client_name = project_name
            report_number = f"AMEC-P-D-2026-Q-{project_number}" if project_number else "Needs Owner Review"
            unresolved = "Needs Owner Review / يحتاج مراجعة المالك"
            unresolved_cell = "مراجعة المالك"
            protected = "محمي - مراجعة بشرية"
            source_text = "\n".join(
                str((entry.get("projection") or {}).get("source_excerpt") or "")
                for entry in context
                if entry.get("context_type") != "DOCUMENT_VERSION"
                or not (entry.get("projection") or {}).get("template_baseline")
            )
            building_matches = re.findall(r"(?:\\b(?:actual|existing|total)?\\s*buildings?\\b|المباني|مبنى|مبانٍ)[^\\d]{0,40}(\\d{1,3})", source_text, flags=re.IGNORECASE)
            building_matches += re.findall(r"(\\d{1,3})[^\\d\\n]{0,20}(?:\\bbuildings?\\b|مبنى|مبانٍ)", source_text, flags=re.IGNORECASE)
            building_count = max((int(value) for value in building_matches if int(value) <= 100), default=0)
            building_count_known = bool(building_matches)

            # Preserve the complete fact pass in the work product.  Unknown
            # values are explicit owner-review decisions; the provider never
            # invents an address, area, licence, price, duration, or building
            # condition from a filename or old proposal.
            field_values = {
                "report.recipient": "مجمع رخص البناء – الجهة المختصة",
                "report.project_name_or_site": project_name,
                "report.number": report_number,
                "report.date": unresolved,
                "owner.name": unresolved,
                "owner.qid_or_cr": unresolved,
                "owner.contact_number": unresolved,
                "site.name_or_description": project_name,
                "site.municipality": unresolved,
                "site.zone": unresolved,
                "site.street": unresolved,
                "site.plot_number": unresolved,
                "site.pin": unresolved,
                "site.plot_area": unresolved,
                "site.coordinates": unresolved,
                "site.current_use": unresolved,
                "site.proposed_use": unresolved,
                "site.inspection_date": unresolved,
                "site.actual_building_count": unresolved,
                "site.general_description": unresolved,
                "site.map_image": "خريطة الموقع — يحتاج مراجعة المالك",
                "site.layout_plan_image": "مخطط توزيع المباني — يحتاج مراجعة المالك",
                "license.previous_building_permit_number": unresolved,
                "license.date": unresolved,
                "license.completion_certificate_number": unresolved,
                "license.licensed_use": unresolved,
                "license.approved_building_count": unresolved,
                "license.actual_building_count": unresolved,
                "license.status": unresolved,
                "license.last_approved_amendment": unresolved,
                "overall_building_condition": unresolved,
                "report.conclusion": "يتم استكمال الخلاصة بعد مراجعة جميع المصادر من المالك.",
                "modifications.rows": unresolved,
                "protected.approval": protected,
            }
            if building_count_known:
                field_values["site.actual_building_count"] = str(building_count)
                field_values["license.actual_building_count"] = str(building_count)
            for index in range(1, 16):
                symbol = chr(64 + index) if index <= 26 else str(index)
                for suffix in ("symbol", "name", "current_use", "licensed_use", "area", "floor_count", "structure_type", "visual_condition", "existing_condition", "existing_or_required_modifications", "proposed_action", "photos", "action_other"):
                    field_values[f"building.{index}.{suffix}"] = symbol if suffix == "symbol" else unresolved

            def replace_token(match: re.Match[str]) -> str:
                key = match.group(1).strip()
                if key in {"protected.approval", "consultant_approval", "stamp", "signature", "protected.signature", "protected.stamp"}:
                    return protected
                # The template uses {idx} in its fixed checkbox label.  It is
                # a structural token, never a project fact.
                if "{idx}" in key:
                    return unresolved
                return str(field_values.get(key, unresolved))

            mutations = []
            mutation_sections: dict[str, set[str]] = {}
            mutation_fields: dict[str, set[str]] = {}
            def section_for_field(field: str) -> str:
                if field.startswith("report."): return "report_identity" if field != "report.conclusion" else "conclusion"
                if field.startswith("owner."): return "owner_data"
                if field.startswith("site."): return "site_data"
                if field.startswith("license."): return "existing_license"
                if field.startswith("building."): return "building_detail"
                if field == "modifications.rows": return "modifications"
                if field == "overall_building_condition": return "overall_condition"
                return "report_identity"

            # The Owner DOCX is a real blank form: its semantic targets are
            # native paragraphs/table cells containing labels and blanks, not
            # synthetic [[tokens]]. Resolve those targets from the actual
            # package blocks and mutate the existing OOXML in place.
            block_values = [str(block.get("value", "")) for block in blocks]
            used_anchors: set[str] = set()
            def add_mutation(block: dict[str, Any] | None, replacement: str, fields: list[str], section: str) -> None:
                if not block or block.get("anchor") in used_anchors:
                    return
                current = str(block.get("value", ""))
                if replacement == current:
                    return
                used_anchors.add(str(block.get("anchor")))
                mutations.append({
                    "anchor": block["anchor"],
                    "expected_xml_hash": block["expected_xml_hash"],
                    "replacement": replacement,
                    "reason": "Populate the Owner-supplied Arabic technical report template from the selected Proposal source set.",
                    "citation_keys": citation,
                })
                mutation_sections.setdefault(section, set()).add(str(block["anchor"]))
                for field in fields:
                    mutation_fields.setdefault(field, set()).add(str(block["anchor"]))

            def first_block(predicate, start: int = 0) -> tuple[int, dict[str, Any]] | None:
                for idx in range(start, len(blocks)):
                    if predicate(block_values[idx]):
                        return idx, blocks[idx]
                return None

            def next_value_block(label: str, *, start: int = 0) -> dict[str, Any] | None:
                found = first_block(lambda value: label in value, start)
                if not found:
                    return None
                idx, _ = found
                for candidate in blocks[idx + 1:]:
                    value = str(candidate.get("value", ""))
                    if value in {"م²", "م²"}:
                        continue
                    if value == "" or "_" in value or value in {"سارية / منتهية / أخرى: __________"}:
                        return candidate
                    # Stop at the next table/paragraph label rather than
                    # stealing a value from another semantic field.
                    if value.strip() and not value.startswith("_"):
                        break
                return None

            header = first_block(lambda value: value.startswith("مقدم إلى:"))
            add_mutation(
                header[1] if header else None,
                f"مقدم إلى: {field_values['report.recipient']} | اسم المشروع / الموقع: {project_name} | رقم التقرير: {report_number} | التاريخ: {field_values['report.date']} | الإصدار: Rev. 00",
                ["report.recipient", "report.project_name_or_site", "report.number", "report.date"],
                "report_identity",
            )
            owner = first_block(lambda value: value.startswith("اسم المالك:"))
            add_mutation(
                owner[1] if owner else None,
                f"اسم المالك: {field_values['owner.name']} | رقم البطاقة / السجل التجاري: {field_values['owner.qid_or_cr']} | رقم التواصل: {field_values['owner.contact_number']}",
                ["owner.name", "owner.qid_or_cr", "owner.contact_number"],
                "owner_data",
            )
            for label, field in (
                ("اسم / وصف الموقع", "site.name_or_description"), ("البلدية", "site.municipality"),
                ("المنطقة Zone", "site.zone"), ("الشارع Street", "site.street"),
                ("رقم القسيمة Plot No.", "site.plot_number"), ("الرقم المساحي / PIN", "site.pin"),
                ("مساحة القسيمة", "site.plot_area"), ("إحداثيات الموقع", "site.coordinates"),
                ("الاستخدام الحالي", "site.current_use"), ("الاستخدام المقترح", "site.proposed_use"),
            ):
                add_mutation(next_value_block(label), str(field_values[field]), [field], "site_data")
            for label, field in (
                ("رقم رخصة البناء القديمة", "license.previous_building_permit_number"),
                ("تاريخ الرخصة", "license.date"),
                ("رقم شهادة إتمام البناء", "license.completion_certificate_number"),
                ("الاستخدام المرخص", "license.licensed_use"),
                ("عدد المباني طبقاً للرخصة", "license.approved_building_count"),
                ("عدد المباني الموجودة فعلياً", "license.actual_building_count"),
                ("حالة الرخصة", "license.status"),
                ("آخر تعديل معتمد", "license.last_approved_amendment"),
            ):
                value = str(field_values[field])
                add_mutation(next_value_block(label), unresolved_cell if value == unresolved else value, [field], "existing_license")
            site_description = first_block(lambda value: value.startswith("الموقع عبارة عن قسيمة"))
            add_mutation(site_description[1] if site_description else None, f"الموقع عبارة عن قسيمة رقم {field_values['site.plot_number']}، بالمنطقة رقم {field_values['site.zone']}، شارع رقم {field_values['site.street']}، وتبلغ مساحتها الإجمالية حوالي {field_values['site.plot_area']} م².", ["site.plot_number", "site.zone", "site.street", "site.plot_area"], "site_description")
            site_count = first_block(lambda value: value.startswith("وفقاً للمعاينة الميدانية"))
            add_mutation(site_count[1] if site_count else None, f"وفقاً للمعاينة الميدانية بتاريخ {field_values['site.inspection_date']}، يحتوي الموقع حالياً على عدد {field_values['site.actual_building_count']} مبنى / منشأة، بالإضافة إلى الأعمال الخارجية والخدمات التابعة للموقع.", ["site.inspection_date", "site.actual_building_count"], "site_description")
            site_general = first_block(lambda value: value.startswith("تمت معاينة الموقع وتصوير"))
            add_mutation(site_general[1] if site_general else None, "تمت مراجعة المستندات والصور والمخططات المتاحة. يجب استكمال المعاينة الميدانية النهائية ورفع الأبعاد الفعلية لجميع المباني والمنشآت قبل اعتماد النسخة النهائية للتقديم للجهة المختصة.", ["site.general_description"], "site_description")
            map_block = first_block(lambda value: value.startswith("[توضع هنا صورة Google Map"))
            add_mutation(map_block[1] if map_block else None, str(field_values["site.map_image"]), ["site.map_image"], "site_map")
            layout_block = first_block(lambda value: value.startswith("توضع هنا صورة Site Plan"))
            add_mutation(layout_block[1] if layout_block else None, str(field_values["site.layout_plan_image"]), ["site.layout_plan_image"], "site_layout")

            detail_blocks = [
                (idx, block) for idx, block in enumerate(blocks)
                if str(block.get("value", "")).startswith("الاستخدام الحالي:")
            ]
            condition_blocks = [
                (idx, block) for idx, block in enumerate(blocks)
                if str(block.get("value", "")).startswith("يظهر من المعاينة الميدانية")
            ]
            modification_blocks = [
                (idx, block) for idx, block in enumerate(blocks)
                if str(block.get("value", "")).startswith("التعديلات القائمة / المطلوبة")
            ]
            for index, (_, detail) in enumerate(detail_blocks, start=1):
                prefix = f"building.{index}."
                detail_text = f"الاستخدام الحالي: {field_values[prefix+'current_use']} | الاستخدام حسب الرخصة السابقة: {field_values[prefix+'licensed_use']} | المساحة: {field_values[prefix+'area']} م² | عدد الطوابق: {field_values[prefix+'floor_count']} | نوع الإنشاء: {field_values[prefix+'structure_type']} | الحالة الظاهرية للمبنى: {field_values[prefix+'visual_condition']}"
                fields = [prefix + suffix for suffix in ("current_use", "licensed_use", "area", "floor_count", "structure_type", "visual_condition")]
                add_mutation(detail, detail_text, fields, "building_detail")
            for index, (_, condition) in enumerate(condition_blocks, start=1):
                prefix = f"building.{index}."
                add_mutation(condition, f"تظهر من المستندات والصور المتاحة حالة المبنى {field_values[prefix+'visual_condition']}. تتم مطابقة الحالة القائمة مع المخططات والمستندات واستكمال القياسات بالموقع.", [prefix + "visual_condition"], "building_detail")
            for index, (_, modification) in enumerate(modification_blocks, start=1):
                prefix = f"building.{index}."
                add_mutation(modification, f"التعديلات القائمة / المطلوبة: {field_values[prefix+'existing_or_required_modifications']}", [prefix + "existing_or_required_modifications"], "modifications")

            # Building inventory rows are native Word table cells. Resolve the
            # first 5 rows from the actual package order and let the structural
            # expander clone/trim those rows for projects with another count.
            inventory_heading = first_block(lambda value: "جدول حصر المباني" in value)
            inventory_start = inventory_heading[0] if inventory_heading else 0
            row_starts = [idx for idx in range(inventory_start, len(blocks)) if block_values[idx] in {"01", "02", "03", "04", "05"}]
            for row_index, row_start in enumerate(row_starts[:15], start=1):
                row = blocks[row_start:row_start + 8]
                if len(row) < 8:
                    continue
                symbol = chr(64 + row_index) if row_index <= 26 else str(row_index)
                add_mutation(row[1], symbol, [f"building.{row_index}.symbol"], "building_inventory")
                for offset, suffix in enumerate(("name", "current_use", "area", "floor_count", "visual_condition", "required_modification"), start=2):
                    value = str(field_values.get(f"building.{row_index}.{suffix}", unresolved))
                    add_mutation(row[offset], unresolved_cell if value == unresolved else value, [f"building.{row_index}.{suffix}"], "building_inventory")

            overall = first_block(lambda value: value.startswith("بناءً على المعاينة البصرية"))
            add_mutation(overall[1] if overall else None, "بناءً على المصادر المتاحة، تم تسجيل الحالة الظاهرية للمباني والمنشآت القائمة. يجب استكمال المعاينة الميدانية النهائية قبل الاعتماد.", ["overall_building_condition"], "overall_condition")
            conclusion = first_block(lambda value: value.startswith("ويقدم التقرير إلى مجمع رخص البناء"))
            add_mutation(conclusion[1] if conclusion else None, "ويقدم التقرير إلى مجمع رخص البناء لدراسة الحالة واتخاذ الإجراءات اللازمة بشأن الطلب، طبقاً للأنظمة والاشتراطات المعمول بها وبعد استكمال التحقق الميداني من المالك والمكتب الاستشاري.", ["report.conclusion"], "conclusion")

            for block in blocks:
                value = str(block.get("value", ""))
                replacement = re.sub(r"\[\[([^\]]+)\]\]", replace_token, value)
                # Support older complete AMEC baselines during migration while
                # ensuring no historical project facts survive.
                if replacement == value:
                    if re.search(r"amec\s*[-_ ]?p\s*[-_ ]?d\s*[-_ ]?\d{4}\s*[-_ ]?q\s*[-_ ]?\d+", value, re.I) and project_number:
                        replacement = re.sub(r"(amec\s*[-_ ]?p\s*[-_ ]?d\s*[-_ ]?\d{4}\s*[-_ ]?q\s*[-_ ]?)\d+", rf"\g<1>{project_number}", value, flags=re.I)
                    elif value.casefold().startswith("project:"):
                        replacement = f"Project: {project_name}"
                    elif value.casefold().startswith("client name:"):
                        replacement = f"Client Name: {client_name}"
                if replacement != value:
                    mutations.append({
                        "anchor": block["anchor"],
                        "expected_xml_hash": block["expected_xml_hash"],
                        "replacement": replacement,
                        "reason": "Populate the canonical Arabic technical report from the selected Proposal source set.",
                        "citation_keys": citation,
                    })
                    for field in re.findall(r"\[\[([^\]]+)\]\]", value):
                        mutation_sections.setdefault(section_for_field(field), set()).add(str(block["anchor"]))
            observed_fields = set()
            for block in blocks:
                observed_fields.update(re.findall(r"\[\[([^\]]+)\]\]", str(block.get("value", ""))))
            observed_fields = {field.replace("{idx}", "1") for field in observed_fields}
            observed_fields.update(mutation_fields)
            fact_pass = []
            for field_id, value in field_values.items():
                if field_id not in observed_fields:
                    continue
                is_protected = field_id == "protected.approval"
                is_confirmed = field_id in {"report.project_name_or_site", "report.number", "site.name_or_description"} and value not in {unresolved, "Needs Owner Review"}
                fact_pass.append({
                    "field_id": field_id,
                    "value": value,
                    "status": "NOT_APPLICABLE" if is_protected else ("SUPPORTED" if is_confirmed else ("NEEDS_OWNER_REVIEW" if value == unresolved or "Needs Owner Review" in value else "NOT_APPLICABLE")),
                    "citation_keys": [] if is_protected else citation,
                    "reason": "Protected human approval field is never completed by AI." if is_protected else ("Identity is anchored to the Proposal/Synology source projection." if is_confirmed else "No authoritative source fact was available; owner review is required."),
                })
            generation_coverage = [{
                "section_id": section,
                "disposition": "NEEDS_OWNER_REVIEW" if section in {"owner_data", "site_data", "existing_license", "building_inventory", "building_detail", "modifications", "overall_condition", "conclusion"} else "POPULATED_FROM_SOURCE",
                "mutation_ids": sorted(mutation_sections.get(section, set())),
                "citation_keys": citation,
                "reason": "Canonical section processed; unresolved fields are explicitly marked for Owner review.",
            } for section in SECTION_KEYS]
            payload = {
                "summary": "Complete source-grounded Arabic technical-report proposal generated from the canonical AMEC template.",
                "baseline_document_version_id": baseline_id,
                "mutations": mutations,
                "citation_keys": citation,
                "template_id": TEMPLATE_ID,
                "template_version": TEMPLATE_VERSION,
                "building_count": building_count,
                "building_count_known": building_count_known,
                "fact_pass": fact_pass,
                "generation_coverage": generation_coverage,
                "draft_only": True,
            }
        else:
            payload = {"summary": "Synthetic governed Contract handoff preflight explanation.", "deterministic_state": "UNKNOWN", "deterministic_blockers": [], "candidate_issues": [], "next_permissible_human_actions": ["Review the preflight inside the Proposal workspace."], "citation_keys": citation}
        return AIProviderResult(f"synthetic-proposal-{name}", payload, AIProviderUsage(1, 1, 2))


@dataclass(frozen=True)
class ProposalContext:
    proposal: Opportunity
    accepted_revision: ProposalAcceptedRevision | None
    working_revision: ProposalRevision | None
    skill: SkillDefinition


def build_proposal_context(db: Session, *, proposal_id: str, operation: str, principal: AuthenticatedPrincipal) -> ProposalContext:
    principal = _principal(db, principal)
    proposal = db.get(Opportunity, proposal_id)
    if proposal is None:
        raise IntelligenceContractError("PROPOSAL_NOT_FOUND")
    skill = _skill(operation)
    accepted = _accepted(db, proposal.id)
    working = _working(db, proposal.id)
    if skill.manifest.skill_id in ACCEPTED_REVISION_SKILLS and accepted is None:
        raise IntelligenceContractError("PROPOSAL_ACCEPTED_REVISION_REQUIRED")
    # Intelligence is read-only with respect to Proposal business state.  A
    # pre-acceptance run may compile the current intake projection when no
    # mutable working revision exists, but only an explicit Proposal-domain
    # command may create that ProposalRevision.
    return ProposalContext(proposal=proposal, accepted_revision=accepted, working_revision=working, skill=skill)


def execute_proposal_intelligence(
    db: Session, *, proposal_id: str, operation: str, principal: AuthenticatedPrincipal,
    idempotency_key: str, correlation_id: str, settings: Settings, provider: Any | None = None,
) -> dict[str, Any]:
    principal = _principal(db, principal)
    context = build_proposal_context(db, proposal_id=proposal_id, operation=operation, principal=principal)
    register_eval_pack(
        db, eval_pack_id=P08_EVAL_PACK_ID, version=P08_EVAL_PACK_VERSION, owning_module="proposal",
        critical_case_policy="ALL_SECURITY_CURRENTNESS_AUTHORITY_CRITICAL",
        acceptance_threshold_policy="CRITICAL_100_PERCENT_NO_SKIPS",
    )
    proposal = context.proposal
    request = SkillExecutionRequest(
        idempotency_key=idempotency_key, correlation_id=correlation_id,
        skill_id=context.skill.manifest.skill_id, skill_version=context.skill.manifest.version,
        skill_manifest_hash=context.skill.manifest.manifest_hash, purpose=context.skill.manifest.purpose,
        execution_mode="INTERACTIVE", scope_type="PROPOSAL", scope_id=proposal.id,
        project_id=proposal.project_id, target_entity_type="PROPOSAL", target_entity_id=proposal.id,
        context_schema_version="proposal-context-v1", policy_version=P08_POLICY_VERSION,
        sources=tuple(_proposal_sources(db, context)),
    )
    # Proposal API execution uses the request transaction's configured
    # database. The shared runtime remains the sole execution path, while a
    # short-lived sibling session keeps reservation/finalization independent
    # without falling back to the process-default database.
    runtime_session = sessionmaker(bind=db.get_bind(), expire_on_commit=False)
    result = SkillRuntime(dependencies=RuntimeDependencies(session_factory=runtime_session)).execute(db, principal, request, settings=_runtime_settings(settings, provider), provider=provider)
    work_product = db.get(AIWorkProduct, result["work_product_id"])
    if work_product is None:
        raise IntelligenceContractError("PROPOSAL_INTELLIGENCE_WORK_PRODUCT_NOT_FOUND")
    _create_work_review(db, proposal=proposal, revision=context.accepted_revision, work_product=work_product, correlation_id=correlation_id)
    db.commit()
    result["current_actionable"] = str(work_product.state) == "CURRENT"
    result["review_actionable"] = True
    result["review_required_capability"] = P08_REVIEW_CAPABILITY
    return result


def _create_work_review(db: Session, *, proposal: Opportunity, revision: ProposalAcceptedRevision | None, work_product: AIWorkProduct, correlation_id: str) -> ProposalIntelligenceReviewBinding:
    existing = db.scalar(select(ProposalIntelligenceReviewBinding).where(ProposalIntelligenceReviewBinding.work_product_id == work_product.id))
    if existing:
        return existing
    review_persona = _review_persona_for_work_product(work_product)
    task = WorkflowTask(
        task_type="PROPOSAL_INTELLIGENCE_REVIEW", title="Review Proposal Intelligence result",
        description="Review the structured Proposal analysis; this does not authorize a protected Proposal action.",
        owner_role="RESPONSIBLE_ENGINEER" if review_persona == "ENGINEERING" else "BUSINESS_DEVELOPMENT", status=WorkflowTaskStatus.OPEN, priority="NORMAL",
        correlation_id=correlation_id, task_family="PROPOSAL_INTELLIGENCE", context_type="PROPOSAL",
        context_id=proposal.id, blocking=False, next_action_code="REVIEW_PROPOSAL_INTELLIGENCE",
        deep_link=f"/proposals/{proposal.id}", evidence_summary={"work_product_id": work_product.id},
    )
    db.add(task)
    db.flush()
    dependency = db.scalar(select(ContextDependency).where(
        ContextDependency.context_snapshot_id == work_product.context_snapshot_id,
        ContextDependency.dependency_type == "DOMAIN_ENTITY_REVISION",
        ContextDependency.dependency_id == proposal.id,
    ))
    if dependency is None:
        raise IntelligenceContractError("PROPOSAL_INTELLIGENCE_REVISION_DEPENDENCY_MISSING")
    binding = ProposalIntelligenceReviewBinding(
        workflow_task_id=task.id, proposal_id=proposal.id, review_subject_type="WORK_PRODUCT",
        review_subject_id=work_product.id, work_product_id=work_product.id,
        context_snapshot_id=work_product.context_snapshot_id, dependency_type=dependency.dependency_type,
        dependency_id=dependency.dependency_id, dependency_version_or_hash=dependency.dependency_version_or_hash,
        required_persona=review_persona, required_capability=P08_REVIEW_CAPABILITY,
        correlation_id=correlation_id, idempotency_key=f"proposal-review:{work_product.id}",
        precondition_version=dependency.dependency_version_or_hash, actionable=True,
    )
    db.add(binding)
    db.flush()
    return binding


def create_candidate_review(
    db: Session, *, proposal_id: str, candidate_id: str, principal: AuthenticatedPrincipal,
    correlation_id: str,
) -> ProposalIntelligenceReviewBinding:
    principal = _principal(db, principal)
    proposal = db.get(Opportunity, proposal_id)
    candidate = db.get(CandidateAssertion, candidate_id)
    if proposal is None or candidate is None or candidate.scope_id != proposal.id or (candidate.target_module and candidate.target_module.lower() != "proposal"):
        raise IntelligenceContractError("PROPOSAL_REVIEW_SCOPE_MISMATCH")
    existing = db.scalar(select(ProposalIntelligenceReviewBinding).where(ProposalIntelligenceReviewBinding.candidate_assertion_id == candidate.id))
    if existing:
        return existing
    task = WorkflowTask(
        task_type="PROPOSAL_INTELLIGENCE_CANDIDATE_REVIEW", title="Review Proposal candidate fact",
        description="Review the candidate fact; Accept/Correct creates a shared VerifiedAssertion only through the human decision command.",
        owner_role="BUSINESS_DEVELOPMENT", status=WorkflowTaskStatus.OPEN, priority="NORMAL",
        correlation_id=correlation_id, task_family="PROPOSAL_INTELLIGENCE", context_type="PROPOSAL",
        context_id=proposal.id, blocking=False, next_action_code="REVIEW_PROPOSAL_CANDIDATE",
        deep_link=f"/proposals/{proposal.id}", evidence_summary={"candidate_assertion_id": candidate.id},
    )
    db.add(task)
    db.flush()
    binding = ProposalIntelligenceReviewBinding(
        workflow_task_id=task.id, proposal_id=proposal.id, review_subject_type="CANDIDATE_ASSERTION",
        review_subject_id=candidate.id, candidate_assertion_id=candidate.id,
        dependency_type="CANDIDATE_ASSERTION", dependency_id=candidate.id,
        dependency_version_or_hash=candidate.value_hash, required_persona="BUSINESS_DEVELOPMENT",
        required_capability=P08_REVIEW_CAPABILITY, correlation_id=correlation_id,
        idempotency_key=f"proposal-candidate-review:{candidate.id}", precondition_version=candidate.value_hash,
        actionable=True,
    )
    db.add(binding)
    db.flush()
    return binding


def refresh_review_currentness(db: Session, binding: ProposalIntelligenceReviewBinding) -> bool:
    if not binding.actionable:
        return False
    dependency = ContextDependency(
        context_snapshot_id=binding.context_snapshot_id or "", dependency_type=binding.dependency_type,
        dependency_id=binding.dependency_id, dependency_version_or_hash=binding.dependency_version_or_hash,
        required=True, trust_state="CANONICAL", currentness_state_at_capture="CURRENT", metadata_json={"domain_entity": "PROPOSAL"},
    )
    current = dependency_current(db, dependency)
    if current and binding.context_snapshot_id:
        current = not bool(revalidate_snapshot(db, binding.context_snapshot_id))
    if not current:
        binding.actionable = False
        binding.stale_reason = "PROPOSAL_INTELLIGENCE_DEPENDENCY_STALE"
        invalidate_dependency(
            db, dependency_type=binding.dependency_type, dependency_id=binding.dependency_id,
            superseding_version_or_hash=None,
            source_event_id=f"proposal-review-currentness:{binding.id}",
            reason_code="PROPOSAL_INTELLIGENCE_DEPENDENCY_STALE",
        ) if binding.work_product_id else None
        if binding.work_product_id:
            work_product = db.get(AIWorkProduct, binding.work_product_id)
            if work_product and str(work_product.state) == "CURRENT":
                work_product.state = "STALE"
                work_product.stale_reason = binding.stale_reason
        task = db.get(WorkflowTask, binding.workflow_task_id)
        if task:
            task.status = WorkflowTaskStatus.BLOCKED
            task.next_action_code = "RERUN_PROPOSAL_INTELLIGENCE"
        db.flush()
    return current


def proposal_reviews(db: Session, proposal_id: str) -> list[dict[str, Any]]:
    rows = db.scalars(select(ProposalIntelligenceReviewBinding).where(ProposalIntelligenceReviewBinding.proposal_id == proposal_id).order_by(ProposalIntelligenceReviewBinding.created_at)).all()
    result = []
    for row in rows:
        refresh_review_currentness(db, row)
        wp = db.get(AIWorkProduct, row.work_product_id) if row.work_product_id else None
        task = db.get(WorkflowTask, row.workflow_task_id)
        citations = []
        if wp is not None:
            citations = [
                {
                    "citation_key": (citation.locator_json or {}).get("citation_key", f"CIT-{citation.ordinal:03d}"),
                    "ordinal": citation.ordinal,
                    "source_type": citation.source_type,
                    "source_id": citation.source_id,
                    "source_version_or_hash": citation.source_version_or_hash,
                    "locator": citation.locator_json,
                }
                for citation in db.scalars(
                    select(IntelligenceCitation)
                    .where(IntelligenceCitation.work_product_id == wp.id)
                    .order_by(IntelligenceCitation.ordinal)
                ).all()
            ]
        result.append({"binding_id": row.id, "workflow_task_id": row.workflow_task_id, "proposal_id": row.proposal_id, "review_subject_type": row.review_subject_type, "review_subject_id": row.review_subject_id, "work_product_id": row.work_product_id, "context_snapshot_id": row.context_snapshot_id, "required_persona": row.required_persona, "required_capability": row.required_capability, "correlation_id": row.correlation_id, "precondition_version": row.precondition_version, "actionable": row.actionable and bool(wp and str(wp.state) == "CURRENT"), "stale_reason": row.stale_reason, "task_status": task.status if task else None, "output": wp.structured_output_json if wp and str(wp.state) == "CURRENT" else (wp.structured_output_json if wp else None), "citations": citations, "work_product_state": str(wp.state) if wp else None, "skill_id": wp.skill_id if wp else None, "skill_version": wp.skill_version if wp else None})
    db.commit()
    return result


def submit_proposal_review(
    db: Session, *, proposal_id: str, binding_id: str, decision: str, idempotency_key: str,
    principal: AuthenticatedPrincipal, correlation_id: str, precondition_version: str,
    correction_payload: dict[str, Any] | None = None, reason: str | None = None,
) -> dict[str, Any]:
    principal = _principal(db, principal)
    proposal = db.get(Opportunity, proposal_id)
    binding = db.get(ProposalIntelligenceReviewBinding, binding_id)
    if proposal is None or binding is None or binding.proposal_id != proposal_id:
        raise IntelligenceContractError("PROPOSAL_REVIEW_NOT_FOUND")
    existing_decision = db.scalar(select(IntelligenceReviewDecision).where(IntelligenceReviewDecision.idempotency_key == idempotency_key))
    if existing_decision is not None:
        if existing_decision.review_subject_id != binding.review_subject_id or existing_decision.decision != decision or existing_decision.precondition_version != precondition_version or existing_decision.reviewer_user_id != principal.user_id:
            raise IntelligenceContractError("INTELLIGENCE_IDEMPOTENCY_KEY_REUSE_MISMATCH")
        return {"decision_id": existing_decision.id, "decision": existing_decision.decision, "work_product_id": existing_decision.work_product_id, "verified_assertion_created": False, "protected_action_executed": False}
    if not refresh_review_currentness(db, binding) or not binding.actionable:
        raise IntelligenceContractError("PROPOSAL_REVIEW_STALE")
    if precondition_version != binding.precondition_version:
        raise IntelligenceContractError("PROPOSAL_REVIEW_PRECONDITION_FAILED")
    require_capability(principal.role, P08_REVIEW_CAPABILITY)
    if principal.role.value != "SYSTEM_ADMIN" and persona_for_role(principal.role) not in _allowed_review_personas(binding):
        raise IntelligenceContractError("PROPOSAL_REVIEW_PERSONA_DENIED")
    if binding.candidate_assertion_id:
        candidate = db.get(CandidateAssertion, binding.candidate_assertion_id)
        if candidate is None or candidate.status != "CURRENT" or candidate.value_hash != binding.dependency_version_or_hash:
            raise IntelligenceContractError("PROPOSAL_REVIEW_STALE")
        decision_row = record_module_review_decision(
            db, principal=principal, owning_module="proposal", review_subject_type="CANDIDATE_ASSERTION",
            review_subject_id=candidate.id, decision=decision, idempotency_key=idempotency_key,
            correlation_id=correlation_id, authorizing_capability=P08_REVIEW_CAPABILITY,
            precondition_version=precondition_version, candidate_assertion_id=candidate.id,
            source_currentness_identity={"proposal_id": proposal.id, "candidate_value_hash": candidate.value_hash},
            correction_payload=correction_payload, reason=reason,
        )
        verified_id = None
        if decision in {"ACCEPT", "CORRECT"}:
            verified_id = promote_verified_assertion_from_decision(db, principal=principal, decision_id=decision_row.id, correction_payload=correction_payload).id
        binding.actionable = False
        task = db.get(WorkflowTask, binding.workflow_task_id)
        if task:
            task.status = WorkflowTaskStatus.COMPLETED
        db.commit()
        return {"decision_id": decision_row.id, "decision": decision_row.decision, "verified_assertion_id": verified_id, "protected_action_executed": False}
    revision = _accepted(db, proposal.id)
    working = _working(db, proposal.id)
    work_product = db.get(AIWorkProduct, binding.work_product_id) if binding.work_product_id else None
    current_revision_hash = _current_revision_identity(
        proposal,
        revision,
        working,
        accepted_required=bool(work_product and work_product.skill_id in ACCEPTED_REVISION_SKILLS),
    )
    if current_revision_hash != binding.dependency_version_or_hash:
        raise IntelligenceContractError("PROPOSAL_REVIEW_STALE")
    wp = work_product
    if wp is None or str(wp.state) != "CURRENT":
        raise IntelligenceContractError("PROPOSAL_REVIEW_STALE")
    decision_row = record_module_review_decision(
        db, principal=principal, owning_module="proposal", review_subject_type=binding.review_subject_type,
        review_subject_id=binding.review_subject_id, decision=decision, idempotency_key=idempotency_key,
        correlation_id=correlation_id, authorizing_capability=P08_REVIEW_CAPABILITY,
        precondition_version=precondition_version, work_product_id=wp.id,
        context_snapshot_id=binding.context_snapshot_id,
        source_currentness_identity={"proposal_id": proposal.id, "accepted_revision_id": revision.id if revision else None, "accepted_revision_hash": revision.content_hash if revision else None, "working_revision_id": working.id if working else None, "working_revision_hash": working.content_hash if working else None},
        correction_payload=correction_payload, reason=reason,
    )
    binding.actionable = False
    task = db.get(WorkflowTask, binding.workflow_task_id)
    if task:
        task.status = WorkflowTaskStatus.COMPLETED
    db.commit()
    return {"decision_id": decision_row.id, "decision": decision_row.decision, "work_product_id": wp.id, "verified_assertion_created": False, "protected_action_executed": False}


def submit_candidate_review(
    db: Session, *, proposal_id: str, candidate_id: str, decision: str, idempotency_key: str,
    principal: AuthenticatedPrincipal, correlation_id: str, precondition_version: str,
    correction_payload: dict[str, Any] | None = None, reason: str | None = None,
) -> dict[str, Any]:
    principal = _principal(db, principal)
    proposal = db.get(Opportunity, proposal_id)
    candidate = db.get(CandidateAssertion, candidate_id)
    if proposal is None or candidate is None or candidate.scope_id != proposal.id or candidate.target_module and candidate.target_module.lower() != "proposal":
        raise IntelligenceContractError("PROPOSAL_REVIEW_SCOPE_MISMATCH")
    require_capability(principal.role, P08_REVIEW_CAPABILITY)
    if candidate.status != "CURRENT" or candidate.value_hash != precondition_version:
        raise IntelligenceContractError("PROPOSAL_REVIEW_STALE")
    row = record_module_review_decision(
        db, principal=principal, owning_module="proposal", review_subject_type="CANDIDATE_ASSERTION", review_subject_id=candidate.id,
        decision=decision, idempotency_key=idempotency_key, correlation_id=correlation_id,
        authorizing_capability=P08_REVIEW_CAPABILITY, precondition_version=precondition_version,
        candidate_assertion_id=candidate.id, source_currentness_identity={"proposal_id": proposal.id, "candidate_value_hash": candidate.value_hash}, correction_payload=correction_payload, reason=reason,
    )
    verified_id = None
    if decision in {"ACCEPT", "CORRECT"}:
        verified = promote_verified_assertion_from_decision(db, principal=principal, decision_id=row.id, correction_payload=correction_payload)
        verified_id = verified.id
    db.commit()
    return {"decision_id": row.id, "decision": row.decision, "verified_assertion_id": verified_id, "protected_action_executed": False}


SECTION_DRAFT_ALLOWLIST = frozenset({
    "EXECUTIVE_SUMMARY",
    "UNDERSTANDING_OF_REQUIREMENTS",
    "METHODOLOGY",
    "SCOPE_OF_SERVICES",
    "DELIVERABLES",
    "PROGRAMME",
    "COMMERCIALS",
    "ASSUMPTIONS",
    "EXCLUSIONS",
})


def apply_section_draft(
    db: Session,
    *,
    proposal_id: str,
    work_product_id: str,
    working_revision_id: str,
    working_revision_hash: str,
    section_type: str,
    edited_content: str,
    principal: AuthenticatedPrincipal,
    correlation_id: str,
) -> dict[str, Any]:
    """Apply a reviewed section draft only to the current mutable revision."""
    principal = _principal(db, principal)
    require_capability(principal.role, "BD_PROPOSAL_WRITE")
    proposal = db.get(Opportunity, proposal_id)
    revision = db.get(ProposalRevision, working_revision_id)
    work_product = db.get(AIWorkProduct, work_product_id)
    if proposal is None or revision is None or revision.proposal_id != proposal_id:
        raise IntelligenceContractError("PROPOSAL_WORKING_REVISION_NOT_FOUND")
    if revision.status != "DRAFT" or revision.content_hash != working_revision_hash:
        raise IntelligenceContractError("PROPOSAL_WORKING_REVISION_STALE")
    if work_product is None or work_product.skill_id != "proposal.section-draft" or str(work_product.state) != "CURRENT":
        raise IntelligenceContractError("PROPOSAL_SECTION_DRAFT_STALE")
    if not edited_content.strip():
        raise IntelligenceContractError("PROPOSAL_SECTION_DRAFT_CONTENT_REQUIRED")
    section_key = section_type.strip().upper().replace(" ", "_")
    if section_key not in SECTION_DRAFT_ALLOWLIST:
        raise IntelligenceContractError("PROPOSAL_SECTION_NOT_ALLOWED")
    decision = db.scalar(select(IntelligenceReviewDecision).where(
        IntelligenceReviewDecision.work_product_id == work_product.id,
        IntelligenceReviewDecision.owning_module == "proposal",
        IntelligenceReviewDecision.decision.in_( ("ACCEPT", "CORRECT") ),
    ).order_by(IntelligenceReviewDecision.decided_at.desc()))
    if decision is None:
        raise IntelligenceContractError("PROPOSAL_SECTION_REVIEW_REQUIRED")
    snapshot = dict(revision.snapshot or {})
    sections = dict(snapshot.get("working_sections") or {})
    sections[section_key] = {
        "content": edited_content,
        "source_work_product_id": work_product.id,
        "review_decision_id": decision.id,
        "applied_by": principal.user_id,
        "correlation_id": correlation_id,
    }
    snapshot["working_sections"] = sections
    revision.snapshot = snapshot
    revision.content_hash = stable_hash(snapshot)
    revision.change_summary = {
        **dict(revision.change_summary or {}),
        "last_intelligence_apply": {
            "section_type": section_key,
            "work_product_id": work_product.id,
            "review_decision_id": decision.id,
        },
    }
    db.flush()
    return {
        "proposal_id": proposal.id,
        "working_revision_id": revision.id,
        "revision_number": revision.revision_number,
        "working_revision_hash": revision.content_hash,
        "section_type": section_key,
        "work_product_id": work_product.id,
        "review_decision_id": decision.id,
        "canonical_state_mutated": False,
        "accepted_revision_mutated": False,
    }
