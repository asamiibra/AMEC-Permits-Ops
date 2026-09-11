# Current Implementation Map

The module implementation is concentrated in `backend/app/services/master_content.py`, `backend/app/api/master_content_routers.py`, `backend/app/services/forms_governance.py`, and the Dashboard surfaces `frontend/src/pages/Dashboard.tsx`, `frontend/src/components/MasterContentForms.tsx`, and `frontend/src/lib/masterContentUi.ts`.

The durable model family is `MasterContentItem`, `Document`, `DocumentVersion`, `MasterContentCategory`, `MasterContentModuleBinding`, `MasterContentDependency`, `MasterContentSourceSection`, `MasterContentSourceProvenance`, `MasterContentGovernanceProfile`, `MasterContentApplicability`, `DefinitionEntry`, and `DefinitionRevision`.

The shared seams are:

- `canonical_master_content_candidates` and `resolve_master_content_purpose` for deterministic consumer resolution.
- exact item/version checks for consumers that persist a binding.
- `source18` for official form, packet, authority-only and submission controls.
- `governed_prefill` and the Evidence models for observations, citations and verified assertions.
- Requirements, preparation, Engineering, Correspondence, Handover and Finance routes for their own canonical state.

The gap-closure commit adds validation and fail-closed checks; it does not add a second source of truth.
