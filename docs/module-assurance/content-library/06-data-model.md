# Data Model and Persistence

Content Library persistence is item/version oriented. `MasterContentItem.current_document_version_id` points to the current `DocumentVersion`; governance, source sections, provenance, applicability, bindings and dependencies are separate durable records. Definitions use `DefinitionEntry` plus `DefinitionRevision`.

The model does not own Project Requirement Items, Project Evidence, AuthorityCase, SubmissionPackage, actual Technical Report revisions, professional approvals, Handover state or Finance state. Those models were inspected and recorded in the ownership ledger.

The exact current version is part of consumer resolution and persisted consumer bindings. A later publication does not silently rewrite a previously accepted consumer snapshot.
