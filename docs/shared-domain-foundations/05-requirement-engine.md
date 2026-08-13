# Requirement Engine v2

Implemented RequirementDefinition, RequirementPolicyVersion with version/effective/provenance/approval fields, RequirementGroup with ALL_OF/ANY_OF/ONE_OF/AT_LEAST_N, policy items, structured evidence constraints, exact source lineage, three-valued applicability, evaluation/evidence evaluation, waiver/N/A/override decision records, and deterministic policy resolution.

The resolver fails closed on no match or ambiguity. Evidence is context-bound and verified; unknown applicability is not treated as N/A. Active policy versions and decisions are audit-protected.
