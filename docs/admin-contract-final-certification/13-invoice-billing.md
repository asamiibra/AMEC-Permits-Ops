# Invoice and Billing

The BillingPlan → BillingPlanRevision → BillingMilestone → Invoice → InvoiceRevision chain is implemented and revision-pinned. Milestone eligibility gates invoice creation; invoice acceptance is distinct from issue. Billing context is read-only from the Contract surface and does not fabricate BillingMilestones.

The full billing lifecycle test passed on PostgreSQL, including plan activation, eligible milestone, draft invoice, revision, acceptance, issue, delivery, acknowledgment, due-date derivation, receivable, payment verification/allocation, and follow-up. Billing V2 browser evidence passed.

