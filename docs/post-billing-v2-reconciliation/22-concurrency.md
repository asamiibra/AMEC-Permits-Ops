# Concurrency and idempotency

PostgreSQL full-suite coverage passed existing invoice-reference allocation and milestone overbilling guards. Billing-v2 delivery retries use a unique idempotency key and the targeted lifecycle test verified one event on retry. Payment allocation retains unique idempotency and invoice allocation constraints. `_allocate_invoice_ref` locks the numbering policy row with `FOR UPDATE`; milestone invoicing checks remaining invoiceable amount transactionally. Result: 0 duplicate references, 0 overbilling, 0 duplicate delivery retries, 0 double allocations observed.
