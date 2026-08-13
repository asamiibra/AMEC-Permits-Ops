# Migration Plan

Four additive migrations follow the actual head and preserve downgrade order:

- `0037_regulatory_core` — regulatory catalog, journey, case, subject, identifiers, work periods, interactions, outcomes, relations.
- `0038_requirement_engine_v2` — definitions, versioned policies, groups, items, evidence constraints, decisions, evaluations, lineage.
- `0039_technical_rule_core` — versioned rule sets, rules, source lineage, evaluations.
- `0040_form_automation_runtime` — profiles, semantic assertions, draft mappings, instances, artifacts, validation, QA, signature seam.

Fresh SQLite and PostgreSQL upgrades reached `0040_form_automation_runtime`; downgrade to `0036_dashboard_forms_governance_wave_a` and re-upgrade also passed. No destructive data rewrite was used.
