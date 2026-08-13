# Upstream token proof

Executable evidence is present in the repository for:

- `ENGINEERING_APPROVED_DESIGN_BASELINE_CODE_FROZEN`
- `ENGINEERING_OWNER_SKETCH_RECONCILIATION_CODE_FROZEN`
- `PREPARATION_SUBMISSION_LOOP_CODE_FROZEN`
- `PERMIT_AUTHORITY_CASE_UX_CODE_FROZEN`
- `ADMIN_CONTRACT_OWNER_SKETCH_RECONCILIATION_CODE_FROZEN`
- `BILLING_INVOICE_CONTRACT_DEPENDENCIES_READY`

The first five are supported by their prior test suites and closure artifacts. The Contract dependency token is supported by the read-only `GET /api/admin/contracts/{contract_id}/billing-context` route and `test_contract_reconciliation_read_model_and_billing_seam`; it does not authorize Invoice implementation. Deployment SHA provenance is unavailable from the checked-in evidence and remains external.
