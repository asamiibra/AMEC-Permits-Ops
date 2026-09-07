# Exact-version binding map

| Consumer | Exact binding | Historical behavior |
|---|---|---|
| Proposal accepted revision | `ProposalAcceptedRevision.template_version_id`, `checklist_version_id`, version numbers and hashes | Accepted revision remains pinned |
| Contract | `ContractTemplateSnapshot.master_content_id`, `document_version_id`, version, hash | Snapshot remains pinned |
| Form Automation | `FormInstance.master_content_item_id`, `source_document_version_id`; `GeneratedArtifact.source_document_version_id` | Current-source mismatch requires revalidation |
| Completion form | Same `FormInstance` fields, case context checked | No silent substitution |
| Preparation/submission | Project/case `DocumentVersion` and package/form pointers | Transactional evidence remains project-bound |
| Definitions | `DefinitionEntry.current_revision_id`; citations use revision ID | Prior business snapshots are not rewritten |

No source bytes are copied into workflow tables and no new version-history model was introduced.
