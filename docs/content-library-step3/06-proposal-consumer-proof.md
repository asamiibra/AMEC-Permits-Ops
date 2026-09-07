# Proposal consumer proof

Proposal template and checklist already used `resolve_master_content_purpose` and persisted exact version/hash fields in `ProposalAcceptedRevision`; they were certified. Definitions use current `DefinitionRevision` projections. The Engineering reference adapter was repaired to call the shared candidate seam, adding current/reviewed/source availability equivalence and preserving exact version/hash/type/discipline fields.

Focused proof: `backend/tests/test_content_library_step3_consumer_convergence.py`; regression: `backend/tests/test_bd_dashboard_integration_followup.py` and Proposal hardening suites.
