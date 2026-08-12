# Deduplication and legacy reconciliation

The 50-key canonical register is unique at the database/API boundary: duplicate key count is `0` and duplicate-truth count is `0`. Legacy Dashboard and Administration input keys are retained as aliases and projected from the canonical item; old audit history is not deleted. Reconciliation imports a legacy confirmation only when an existing legacy record has an actual confirmer and confirmed state.
