# Delivery due-date E2E

The Billing lifecycle test records a 30-day `DELIVERY_DATE` rule, issues the invoice with no due date, observes `AWAITING_DUE_EVENT`, records delivery on 2026-08-14, and verifies due date 2026-09-13. The same test records acknowledgment separately and verifies the communication state changes to ACKNOWLEDGED. Retry with the same delivery key returns the same event row.
