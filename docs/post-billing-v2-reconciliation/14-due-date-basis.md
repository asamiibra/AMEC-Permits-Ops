# Due-date basis

Supported bases are `INVOICE_DATE`, `ISSUE_DATE`, `DELIVERY_DATE`, `ACKNOWLEDGMENT_DATE`, `CLIENT_APPROVAL_DATE`, `FIXED_DATE`, and `OTHER_VERIFIED_EVENT`. The revision pins basis, offset/fixed date, source event type/id, status, and derivation time. Event-based bases remain `PENDING_EVENT` and receivables report `AWAITING_DUE_EVENT`; no overdue state is produced without a valid due date.

Issue-date, delivery-date, and client-approval derivation are deterministic and do not re-evaluate from later Contract terms.
