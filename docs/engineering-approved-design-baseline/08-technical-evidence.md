# Technical evidence

Status: `IMPLEMENTED_AND_VERIFIED`

Technical checks persist exact `TechnicalRuleSetVersion`, `TechnicalRule`, inputs, calculated values, version, result, reason, and lineage. Outcomes are deterministic `PASS`, `FAIL`, or `UNKNOWN`; unknown never passes. Calculation records preserve input units, normalized units, result, hash, and exact rule-set reference. Engineering does not copy technical thresholds.
