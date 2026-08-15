# Proposal detail API contract

`GET /api/bd/proposals/{proposal_id}` remains the read contract for the existing Proposal workspace and is protected by `BD_PROPOSAL_READ`. A successful response is an object with required `id`, `title`, and `stage` plus the established Proposal fields.

The frontend now validates those core fields and normalizes optional collections before rendering. Optional contract areas include `sources`, `stakeholders`, `regulatory_scoping`, `engineering_contributions`, `external_cost_assumptions`, `notes`, `client_responses`, `revision_history`, `forms_v2`, `hardening`, `validation`, `intake_readiness`, `outputs`, `configuration`, `proposal_breakdown`, and `authority`. An HTTP/API failure remains an error; it is not converted into a fake empty Proposal.

The controlled states are: loading, typed contract failure, not-found/unavailable error with Retry and Proposal-list actions, and the fully rendered workspace. The detail route is canonical at `/opportunities/{id}` and supports direct navigation and refresh.
