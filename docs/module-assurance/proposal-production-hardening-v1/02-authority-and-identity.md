# Authority and identity

Implemented: Proposal actor helpers ignore caller-supplied actor values, `current_user_role` binds the verified principal to request state, and audit rows persist auth mode, user/object ID, tenant, office, and role alongside correlation ID/capability at the command boundary. Context cleanup prevents cross-request leakage. Evidence: `backend/tests/test_proposal_production_guards.py`, auth boundary suite. Entra acceptance remains `BLOCKED_EXTERNAL` without a real tenant/token.
