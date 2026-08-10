# Forms E2E

Forms use canonical `F-xxxx` identity, verified SOR writes, current v1/v2/v3 history, stable metadata, Used In bindings, and exact historical download. Administration and Dashboard read the same `MasterContentItem`; metadata changes do not create a new `DocumentVersion`. The deployed browser parity suite is green at 2/2, and the full deployed suite is green at 21/21.

Dedicated BD, Permit, Proposal, and Contract form pickers are not present in the current product. Their canonical eligibility/binding seams are recorded as no-current-consumer rows in the matrix.

Results: `FORM_CREATE_E2E_PASS`, `FORM_SOR_WRITE_READBACK_E2E_PASS`, `FORM_V1_CURRENT_E2E_PASS`, `FORM_DETAIL_E2E_PASS`, `FORM_ADMIN_CANONICAL_PARITY_E2E_PASS`, `FORM_ADMIN_METADATA_PARITY_E2E_PASS`, `FORM_ADMIN_VERSION_PARITY_E2E_PASS`, `DUPLICATE_ADMIN_FORM_TRUTH_ZERO`.
