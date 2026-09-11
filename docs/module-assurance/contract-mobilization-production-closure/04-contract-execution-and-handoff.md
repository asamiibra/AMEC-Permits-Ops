# Execution, distribution, and Operations handoff

Execution evidence is pinned to the accepted Contract revision and exact
DocumentVersion. `CLIENT_COPY_DISTRIBUTION` and `OPERATIONS_HANDOFF` are
separate ContractAdminEvidence rows with actor, timestamp, revision, reference,
audit event, and idempotent replay behavior. Operations handoff is denied until
client-copy distribution exists.

POSITIVE_TEST=backend/tests/test_admin_contract_owner_session.py::test_contract_execution_distribution_and_operations_handoff_are_distinct_and_persisted
