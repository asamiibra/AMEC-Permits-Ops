# E1 shared-control reuse

No assistant-specific evidence, approval, task, audit, or lineage tables were introduced. E1 reuses:

- `Document` / `DocumentVersion` for RFQ, tender, attachments, drawings, and source references.
- `EvidenceArtifact` as a shared evidence pointer for new term/delivery relationships.
- `Approval` through typed quotation, contract, communication, invoice, and handover associations.
- `WorkflowTask`, `NotificationEvent`, and `AuditEvent` remain the existing workflow/control substrate.
- `LineageEdge` carries the new upstream/downstream relationships.
- `TargetRenderingRule` and `DocumentValidity` remain the rendering and validity primitives.

New tables are semantic context records, not replacement control engines.
