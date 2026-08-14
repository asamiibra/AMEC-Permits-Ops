# Targeted PostgreSQL certification

`backend/tests/test_handover_final_closure_bridge.py` is PostgreSQL-only and passed **7 tests** on a fresh database. Coverage includes service-scoped lifecycle, readiness/renditions, immutable revision behavior, policy and RBAC boundaries, financial/regulatory/archive separation, terminal idempotency, concurrent revision allocation, concurrent locking, and global-role invariants.

