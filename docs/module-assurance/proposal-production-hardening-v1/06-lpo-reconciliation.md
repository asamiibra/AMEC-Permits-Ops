# LPO reconciliation

Production LPO reconciliation requires an exact stored LPO DocumentVersion containing authoritative `lpo_fields`, derives amount/currency/scope from the accepted revision, computes variances server-side, and records `SERVER_LPO_COMPARATOR_V1`. Caller-supplied variance lists are TEST-only. Missing fields and mismatches fail closed. Native SQL/database qualification is not claimed without the external gate.
