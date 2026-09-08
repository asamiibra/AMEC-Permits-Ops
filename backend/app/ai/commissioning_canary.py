"""DB-free D3 commissioning canary for the exact application image.

The canary uses the production provider and validators, but only hard-coded
synthetic evidence.  It never opens a SQL, Synology, SMB, or business-data
connection and cannot create an execution-ledger row.
"""

from __future__ import annotations

import json
from dataclasses import asdict

from ..config.settings import Settings
from ..services.governed_retrieval import RetrievalCitation
from .citations import build_evidence, validate_citations
from .contracts import (
    AIContextItem,
    AIContextManifest,
    AIContextScope,
    AIExecutionMode,
    AIManifestPolicy,
    AIPurpose,
    AITargetEntityType,
    ARCHITECTURE_CONTRACT_VERSION,
    MANIFEST_CONTRACT_VERSION,
    POLICY_VERSION,
)
from .orchestration import D3_TASK, STATIC_INSTRUCTIONS
from .provider import AIProviderRequest, AzureOpenAIResponsesProvider
from .runtime_binding import AIRuntimeBinding
from .structured_output import validate_draft


def _manifest() -> AIContextManifest:
    items = tuple(
        AIContextItem(
            canonical_domain="MASTER_CONTENT",
            canonical_entity_type="ENGINEERING_METHOD_STATEMENT",
            canonical_entity_id=entity_id,
            master_content_id=entity_id,
            verification_state="VERIFIED",
            authority_source_class="SYNTHETIC_COMMISSIONING",
            content=f"Synthetic commissioning evidence {citation}: use only for this canary.",
            citation=RetrievalCitation(
                canonical_domain="MASTER_CONTENT",
                canonical_entity_type="ENGINEERING_METHOD_STATEMENT",
                canonical_entity_id=entity_id,
                document_id=document_id,
                document_version_id=version_id,
                locator_type="DOCUMENT_VERSION",
                locator=f"synthetic://{citation}",
                source_hash=f"synthetic-{citation.lower()}",
            ),
        )
        for citation, entity_id, document_id, version_id in (
            ("CIT-001", "SYNTH-ENGINEERING-001", "SYNTH-DOC-001", "SYNTH-V1-001"),
            ("CIT-002", "SYNTH-ENGINEERING-002", "SYNTH-DOC-002", "SYNTH-V1-002"),
        )
    )
    return AIContextManifest(
        purpose=AIPurpose.ENGINEERING_TECHNICAL_DRAFT,
        execution_mode=AIExecutionMode.INTERACTIVE,
        scope=AIContextScope(
            project_id="SYNTHETIC-COMMISSIONING-PROJECT",
            target_entity_type=AITargetEntityType.PROJECT,
            target_entity_id="SYNTHETIC-COMMISSIONING-PROJECT",
        ),
        policy=AIManifestPolicy(
            purpose_id=AIPurpose.ENGINEERING_TECHNICAL_DRAFT,
            required_capabilities=("structured_output", "citation_grounding"),
        ),
        retrieval_contract_version="1.0",
        items=items,
        manifest_fingerprint="commissioning-canary-no-db",
    )


def run() -> dict[str, object]:
    settings = Settings()
    binding = AIRuntimeBinding.from_settings(settings)
    binding.validate()
    manifest = _manifest()
    evidence = [asdict(item) for item in build_evidence(manifest)]
    provider_input = json.dumps(
        {
            "instructions": STATIC_INSTRUCTIONS,
            "task": D3_TASK,
            "project_scope": "synthetic-commissioning-only",
            "evidence": evidence,
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    result = AzureOpenAIResponsesProvider(settings).execute_structured(
        AIProviderRequest(provider_input=provider_input, max_output_tokens=settings.ai_max_output_tokens)
    )
    draft = validate_draft(result.payload)
    citations = validate_citations(draft, manifest)
    return {
        "status": "COMMISSIONED",
        "provider_response_id": result.response_id,
        "usage": asdict(result.usage),
        "runtime_binding": binding.as_dict(),
        "schema_valid": True,
        "citation_keys": sorted(citations),
        "citation_validation": "PASSED",
        "synthetic_evidence_ids": [item.canonical_entity_id for item in manifest.items],
        "draft_only": draft.draft_only,
        "canonical_state_mutated": False,
        "protected_action_count": 0,
        "database_accessed": False,
        "business_rows_written": False,
        "historical_architecture_contract": {
            "architecture_version": ARCHITECTURE_CONTRACT_VERSION,
            "manifest_contract_version": MANIFEST_CONTRACT_VERSION,
            "policy_version": POLICY_VERSION,
        },
    }


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, sort_keys=True))
