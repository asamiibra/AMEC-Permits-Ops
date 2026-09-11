# Contract start prerequisites

`contract_start_prerequisites()` reads exact executed evidence, client-copy and
Operations handoff, ProjectActivation, ContractPaymentTerm, Billing invoice
revision, PaymentReceipt verification, and InvoicePaymentAllocation. Advance is
`NOT_APPLICABLE` unless an exact advance term or configured gate exists. A
payment that is only observed or verified but not allocated does not satisfy the
required advance.

RESULT=CLOSED_AND_PROVEN_LOCALLY
