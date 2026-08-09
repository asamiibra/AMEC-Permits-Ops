# Authority state comparison contract

`AuthorityStateComparison` compares normalized status, repetition, and stable comment keys while preserving raw values. Status/repetition transitions and new official comments are material; cosmetic capture timestamps are excluded. Results are `NO_CHANGE`, `MATERIAL_CHANGE`, `NON_MATERIAL_CHANGE`, or `NEEDS_REVIEW`.
