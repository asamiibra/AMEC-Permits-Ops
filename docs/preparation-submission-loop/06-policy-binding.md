# 06 · Exact requirement policy binding

Status: IMPLEMENTED

Requirement initialization resolves exactly one ACTIVE, effective policy for the case's canonical body, jurisdiction, and service. Zero policies returns `NO_POLICY`; multiple matches return `AMBIGUOUS_POLICY`; no first-row or latest fallback is used. Every case item is materialized as a RequirementInstance with `APPLICABILITY_UNKNOWN` until governed.
