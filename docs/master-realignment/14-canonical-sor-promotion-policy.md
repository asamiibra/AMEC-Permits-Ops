# G11 — Canonical SOR promotion policy

Status: `CANONICAL_SOR_PROMOTION_POLICY_PASS` for the local implementation and tests. A deployed end-to-end upload/promotion cycle remains unverified.

## Policy

`COPY_VERIFY_AND_ARCHIVE_SOURCE` is the deterministic policy. A provisional source is copied into the canonical AMEC project SOR through the configured semantic folder mapping. The copied target is read back and verified before the Project Artifact Record becomes authoritative. The original provisional file and reference remain retained as historical evidence; they are never deleted or silently overwritten.

Promotion is allowed only when the target Project exists with a canonical Project Reference, its Synology root resolves, the configured folder template matches, and the source-to-project identity check passes. Otherwise the operation is `NO PROMOTION`.

Applicable source classes are `TENDER_EMAIL_SOURCE`, `TENDER_DOCUMENT_SOURCE`, `TENDER_IMAGE_SOURCE`, `CLIENT_SOURCE`, and `PROPOSAL_SOURCE`. The mapping is held in `SEMANTIC_FOLDER_CONFIG`; the provisional intake folder is never reused as a guessed canonical destination.

## Required sequence and states

The service performs: resolve source → resolve canonical target → verify source hash/size → copy through the existing adapter → read target → verify target hash/size/path → register canonical binding → mark the provisional binding `HISTORICAL` with `promotion_state=CANONICAL_VERIFIED` → write a lineage edge and audit event.

Controlled states are `PROVISIONAL`, `PROMOTING`, `CANONICAL_VERIFIED`, `PROMOTION_FAILED`, and `CONFLICT`. Missing source, source hash mismatch, unavailable root, folder drift, invalid root, registration failure, and target filename/hash conflict are explicit errors. Partial progress remains recoverable because already verified canonical records are idempotently reused.

The idempotency key is `promotion:{provisional_artifact_id}:{project_id}`. A retry produces no duplicate authoritative Project Artifact Record, DocumentVersion, promotion lineage edge, or promotion audit transition. Cross-project promotion is rejected before any write; the audit metadata records `cross_project_artifact_write=0`.

Evidence: `backend/tests/test_proposals_main.py::test_provisional_sources_promote_to_canonical_sor_idempotently`, `artifacts/master-realignment/sor-promotion-result.json`.
