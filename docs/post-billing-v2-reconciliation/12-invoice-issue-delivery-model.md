# Invoice issue and delivery model

`InvoiceIssueEvent` means official invoice reference allocation and exact rendered artifact creation. It does not send email, upload to a portal, or prove receipt. `InvoiceDeliveryEvent` is a separate Owner-only, idempotent record with channel, recipient snapshot, timestamps, evidence version, status, notes, and lineage. The communication projection distinguishes DRAFT, ACCEPTED, ISSUED, DELIVERED, ACKNOWLEDGED, and CLIENT_APPROVED.
