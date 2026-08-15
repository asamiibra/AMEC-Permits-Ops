# RBAC Audit

Server-side capability checks remain in the canonical Master Content and governance routers. Owner roles retain write actions; Business Development and Engineering retain their scoped read/use behavior. Promotion changed route ownership and presentation only; it did not widen backend permissions.

Evidence: `test_admin_owner_ready.py`, `test_admin_contract_owner_session.py`, `test_dashboard_v2_waves_b_c.py`, and the full PostgreSQL suite.
