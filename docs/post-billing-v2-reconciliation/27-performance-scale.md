# Performance and scale

PostgreSQL query-plan checks used the final schema. Invoice list used `ix_invoices_project_id` and the primary key for current revision; delivery history used `ix_invoice_delivery_invoice_time` backward with execution time 0.012 ms on the certification database. The new delivery/acknowledgment invoice/time and idempotency indexes are present.

A 500-contract/1,000-invoice synthetic scale load was not run; no scale result is claimed. Owner-scale rehearsal remains a pending operational decision, while the indexed query shape and no-new-N+1 detail path were reviewed.
