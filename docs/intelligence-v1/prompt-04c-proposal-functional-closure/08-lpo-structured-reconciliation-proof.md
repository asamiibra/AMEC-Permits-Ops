# Structured LPO reconciliation proof

Structured reconciliation supports scope, fee_value, currency, duration_period, payment_terms, inclusions, and exclusions. Every applicable row requires a client value and MATCH/MISMATCH/NOT_APPLICABLE disposition; NOT_APPLICABLE requires a reason. PASS is derived only when all rows are complete and no row is MISMATCH.

Legacy synthetic fixture payloads remain readable for historical regression tests. Production-shaped callers use comparisons and exact client evidence identity.
