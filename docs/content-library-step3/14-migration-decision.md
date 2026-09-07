# Migration decision

`MIGRATION_CREATED=0`.

Existing fields already represent exact durable lineage: MasterContentItem ID, DocumentVersion ID, version number, hash, ContractTemplateSnapshot, ProposalAcceptedRevision, FormInstance, GeneratedArtifact, package evidence, and DefinitionRevision. The Step 3 repair is a shared service seam and validation only; no additive schema was necessary.
