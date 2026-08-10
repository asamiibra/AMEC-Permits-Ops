# Current-page audit

The existing business navigation already exposes `Proposals & Contracts` at `/proposals-contracts` (with `/permits` retained as a compatibility alias). The previous surface was permit-centric and did not provide a single owner-oriented commercial dashboard or manual source-to-SOR intake.

The revision adds `frontend/src/ProposalsContracts.tsx` and routes that page through the existing business navigation. It reuses the existing `Project`, `Opportunity`, `Quotation`, `Contract`, `ReferenceNumber`, `DocumentVersion`, `EvidenceArtifact`, `LineageEdge`, and audit primitives.

The write boundary is `backend/app/services/proposals_sor.py` over the existing `MockSynologyAdapter` and `SynologyProjectBootstrap` configuration.
