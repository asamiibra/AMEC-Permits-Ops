# Exact-version pinning and lineage

Existing typed models safely represent the required relationships; no second pin table is introduced.

| Consumer | Exact lineage fields | Historical rule |
|---|---|---|
| Accepted Proposal | `ProposalAcceptedRevision` template/checklist item refs, `DocumentVersion` IDs, version numbers, hashes | accepted revision is immutable |
| Contract | `ContractTemplateSnapshot.master_content_id`, `document_version_id`, version, hash | snapshot is immutable |
| Form runtime | `FormInstance.master_content_item_id`, `source_document_version_id`; `GeneratedArtifact` source version | source drift requires revalidation |
| Definitions | `DefinitionEntry.current_revision_id` and revision projections | historical snapshots are not rewritten |
| Transactional evidence | domain-owned `DocumentVersion` and package pointers | project/case scope remains authoritative |

The producer still owns canonical writes. A consumer can reference a master identity and exact version but never copies master bytes or creates a competing master record.
