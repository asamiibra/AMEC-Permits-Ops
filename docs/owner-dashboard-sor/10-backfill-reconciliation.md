# Backfill reconciliation

No existing global master binary was auto-backfilled. Existing `ProjectArtifactRecord` and `DocumentVersion` rows are project-scoped transactional evidence and remain project content. Existing synthetic `FormTemplate`/`FormTemplateVersion`, quotation templates, and regulation placeholders are configuration or non-authoritative stand-ins, not verified global SOR binaries. The reconciliation artifact records this conservative classification and avoids duplicate uploads.
