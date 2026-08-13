# Client acknowledgment

`InvoiceAcknowledgment` is optional and separately recorded by Owner with an idempotency key, reference, timestamp, optional source DocumentVersion, status, and lineage. It does not imply Client Approval. Client approval/certification remains an `InvoiceApprovalRecord` and only approved client approval types advance the approval communication state.
