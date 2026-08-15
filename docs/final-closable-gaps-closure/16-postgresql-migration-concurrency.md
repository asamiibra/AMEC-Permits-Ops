# PostgreSQL, Migration, and Concurrency

Current head is `0054_bd_proposal_stage1_reconciliation`. Head↔`0053_handover_admin_closeout` downgrade/upgrade roundtrip passed on fresh PostgreSQL. Full historical `downgrade base` remains unsupported at a pre-existing dependent-FK boundary; it is not required for forward deployment and is documented rather than misreported as passing.

Full PostgreSQL suite: `202 passed, 2 warnings`. SQLite compatibility suite: `190 passed, 8 skipped, 2 warnings`.
