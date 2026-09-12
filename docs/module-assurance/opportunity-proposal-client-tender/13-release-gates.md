# Release gates

Required final markers:

```text
FINAL_RESULT=OPPORTUNITY_PROPOSAL_CLIENT_TENDER_MODULE_CLOSED
MODULE_ASSURANCE=PASS
MODULE_NEXT_RELEASE_READY=true
FAIL_COUNT=0
BLOCKED_COUNT=0
DATABASE_ALEMBIC_HEAD=opportunity_proposal_idempotency_v1
CANONICAL_SQL_MIGRATION_RESULT=PASS
CANONICAL_SQL_PERSISTENCE_RESULT=PASS
```

These markers describe the scoped module assurance result. Uncompleted deployment and governed-review gates remain documented as later gates.
