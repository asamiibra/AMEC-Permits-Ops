# Approved-vs-As-Built Comparison

Status: IMPLEMENTED_AND_VERIFIED.

`AsBuiltComparisonRun` compares structured approved and AS_BUILT snapshots under a rule version and reference fingerprint. Differences become durable `AsBuiltVariance` rows; the comparison result is deterministic and idempotent.
