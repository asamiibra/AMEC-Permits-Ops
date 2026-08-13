# Audit and lineage

Billing lineage remains Contract/ContractRevision → BillingPlanRevision → BillingMilestone → InvoiceRevision → InvoiceIssueEvent → InvoiceDeliveryEvent → InvoiceAcknowledgment/ApprovalRecord → PaymentReceipt → InvoicePaymentAllocation. Delivery, acknowledgment, approval, payment, and allocation actions each have audit evidence and idempotency controls. No settlement, ledger, bank, or send side effect was added.
