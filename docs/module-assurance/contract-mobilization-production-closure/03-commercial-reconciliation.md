# Commercial reconciliation

`commercial_reconciliation()` compares accepted Proposal and current Contract
amount, currency, duration, payment terms, and scope; structured PO/LPO
assertions are compared when present. Mismatch is fail-closed and requires human
reconciliation. Existing Billing/Contract tests cover the exact accepted
revision and material variance boundary.

RESULT=CLOSED_AND_PROVEN
SOURCE_OF_RECORD=backend/app/services/business_v1_controls.py
