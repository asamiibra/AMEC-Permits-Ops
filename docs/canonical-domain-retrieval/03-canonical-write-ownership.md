# Phase 2 — Canonical write ownership

`DUPLICATE_MASTER_CONTENT_MUTATION_IMPLEMENTATION_COUNT=0`

The canonical master-content command owner is `backend/app/services/master_content.py`:

- create: `create_master_content()`;
- new binary/version: `create_master_content_version()`;
- archive: `archive_master_content()`;
- module bindings/dependencies: the binding/dependency helpers in the same service;
- governance/currentness/provenance: `services/forms_governance.py`, attached to the same master item/version;
- definitions: definition commands in the master-content service, preserving `DefinitionRevision` authority.

Dashboard, Administration, source intake, and compatibility/configuration
routers call these commands or project their results. They do not create a
second master table, write a shadow current-version pointer, or copy source
bytes into a retrieval store.

`MASTER_CONTENT_SINGLE_WRITE_OWNER_PASS=1`
