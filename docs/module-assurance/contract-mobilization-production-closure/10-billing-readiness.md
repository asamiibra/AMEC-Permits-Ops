# Billing readiness

Operations reads canonical BillingPlan/BillingPlanRevision/BillingMilestone and
InvoiceRevision state. An eligible milestone can surface `READY_TO_INVOICE` or
`EARNED_BUT_NOT_INVOICED`; no Invoice is issued by the projection. Invoice
preparation, acceptance, issue, receivable, payment, and settlement remain
Finance-owned actions.

RESULT=CLOSED_AND_PROVEN_LOCALLY
