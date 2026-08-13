# Deployment status

The repository can prove the final local commit and remote parity after push, but it cannot prove a separately deployed production SHA from the available environment. Therefore the following remain truthful external blockers:

- `POST_BILLING_V2_RECONCILIATION_DEPLOYMENT_PROVENANCE_BLOCKED_EXTERNAL`
- `BILLING_INVOICE_DEPLOYMENT_PROVENANCE_BLOCKED_EXTERNAL`
- `REAL_SYNOLOGY_VERIFICATION_BLOCKED_EXTERNAL`
- `REAL_AUTHORITY_SUBMISSION_VERIFICATION_NOT_PERFORMED`
- `REAL_INVOICE_ISSUANCE_NOT_PERFORMED`
- `REAL_INVOICE_DELIVERY_NOT_PERFORMED`
- `REAL_PAYMENT_VERIFICATION_NOT_PERFORMED`
