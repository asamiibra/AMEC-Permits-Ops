# Invoice Source Evidence Matrix

| Source element | Classification | Implementation boundary |
|---|---|---|
| Invoice Ref, date, due date, client, project, lines, totals, amount in words | SOURCE_SAMPLE_ONLY / NORMALIZED | Typed fields and deterministic renderer; values are not copied from the absent sample. |
| Full Contract Amount and 50% advance examples | SOURCE_SAMPLE_ONLY | Informational display and milestone basis are separate; no hard-coded policy. |
| Approval Ref, Reference No., LC-like field | PRODUCTION_POLICY_PENDING | Typed configurable references with no inferred semantics. |
| Payment method, bank/IBAN, account type/currency, account holder, signatory | PRODUCTION_POLICY_PENDING / DEFERRED | Versioned financial account with masked output; no source value entered. |
| Finite line grid | NORMALIZED | Relational InvoiceLineItem rows with no silent truncation. |

The referenced `INV-Form.docx` was absent from the workspace and remains REFERENCE_ONLY / BLOCKED_EXTERNAL.
