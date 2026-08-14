# Financial Settlement

Settlement consumes a read-only canonical Billing snapshot. Open/unverified invoices block settlement; zero receivable is not treated as settled. The settlement endpoint returns `billing_mutated: false`.
