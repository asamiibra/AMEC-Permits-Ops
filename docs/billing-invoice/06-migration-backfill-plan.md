# Migration and backfill plan

Migration `0048_billing_invoice_full` is additive. Existing synthetic E5/E6 Invoice records remain readable; their new canonical fields are nullable and are not invented/backfilled. New Billing plans, milestones, issued invoices, financial-account versions, payment receipts, and allocations are created only through the new governed routes. No historical billing/payment/invoice numbers or bank details are fabricated.
