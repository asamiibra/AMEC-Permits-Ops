# Invoice register and lanes

Administration `/admin/invoices` reuses `BillingInvoicePage` and `/api/billing/invoices`. The list is server-derived and supports All, Need Action, Authority Review, Ready / Close, backend search, Contract/Project context, Amount, Due Date, Stage, and Open. Invoice lifecycle and Receivable state remain separate projections.
