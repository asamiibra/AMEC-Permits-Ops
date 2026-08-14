# Migration Roundtrip

Fresh PostgreSQL upgrade from empty reached one migration head: `0051_construction_inspection_idempotency`. A second isolated database upgraded from pre-Construction revision `0049_billing_v2_communication_due_events` through the Construction revisions, downgraded, and re-upgraded successfully. No multiple-head condition was observed.
