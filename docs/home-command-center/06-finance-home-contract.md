# Finance Home contract

The Home Finance card is a compact summary, not a replacement for `/billing`. It reads the existing billing summary and invoice projection, shows invoices due, payments to review, and a settlement status, and links to the canonical Finance workspace.

If an invoice projection lacks both a usable amount and currency, Home displays `No issued balance` rather than deriving or formatting a false amount. No invoice, payment, accounting, or workflow mutation is performed.
