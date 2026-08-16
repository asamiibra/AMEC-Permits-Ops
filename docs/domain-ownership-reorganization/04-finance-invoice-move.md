# Finance and Invoice move

`/billing` is the canonical Finance workspace. `BillingInvoicePage` now labels the surface as Finance and retains the existing Billing Plan, Billing Milestone, Invoice, InvoiceRevision, Receivable, human Accept/Issue, communication, payment, and allocation API boundary.

The Contract workspace exposes only a Finance summary and an `Open Finance` link. It does not duplicate Invoice management. The Contract-to-Finance linkage remains contextual and uses the existing billing read model.

No billing lifecycle predicate, invoice identity, numbering, financial-account pinning, receivable state, payment evidence, verification, allocation, or settlement service was changed.
