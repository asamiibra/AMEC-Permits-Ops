# Architecture reconciliation

The repository already had `Document`, `DocumentVersion`, `EvidenceArtifact`, `LineageEdge`, `MaterialChangeEvent`, `DocumentValidity`, `AuditEvent`, and a synthetic `MockSynologyAdapter`. Project documents require project scope, so the model was extended to allow a null project for AMEC-level master content while retaining existing project records unchanged. `MasterContentItem` supplies stable business identity and points to the reused `Document`/`DocumentVersion` history.

The repository has no real Synology transport or credentials. The checked-in mapping is explicitly synthetic and deployment-configurable through `MASTER_SOR_MAPPING_JSON`.
