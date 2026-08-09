# Finding recurrence key contract

Recurrence identity is deterministic and code/configuration-owned. `FindingCode.recurrence_key_strategy` selects `CODE_ONLY`, `CODE_PLUS_AFFECTED_OBJECT`, `CODE_PLUS_REQUIREMENT`, `CODE_PLUS_PORTAL_SECTION`, `EXTERNAL_FINDING_ID`, or `HUMAN_REVIEW_REQUIRED`.

The Week 13 service emits a stable key from the selected code, source family, discipline, requirement, and affected object where configured. Missing/ambiguous code identity becomes `POSSIBLE_RECURRENCE_NEEDS_REVIEW`; no fuzzy or LLM matching is used.
