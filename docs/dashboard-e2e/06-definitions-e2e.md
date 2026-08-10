# Definitions E2E

Definitions use canonical `D-xxxx` identity, current revision lookup, immutable revision history, Used In metadata, and notifications on revision promotion. `GET /api/definitions/lookup/{term}` resolves the current revision; historical persisted business records do not point to a mutable replacement. Dedicated downstream definition-picker UIs are not present, so those rows use the verified lookup seam classification.

Results: `DEFINITION_CREATE_E2E_PASS`, `DEFINITION_REVISION_E2E_PASS`, `DEFINITION_HISTORY_E2E_PASS`, `DEFINITION_CURRENT_LOOKUP_E2E_PASS`, `DEFINITION_HISTORICAL_REWRITE_ZERO`.
