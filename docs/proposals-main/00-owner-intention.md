# ProposalOps — owner intention

The Proposals & Contracts main page is an owner-facing commercial work surface.

- Orange means a person is manually providing a source file or source context.
- Blue means ProposalOps is showing system-derived state, counts, and records.
- The project/reference is selected before any source can be written.
- ProposalOps resolves the configured AMEC project-folder destination, writes to the synthetic SOR adapter, reads the file back, verifies hash and size, then registers workflow/index metadata.
- ProposalOps is not a replacement document repository; the configured project-folder repository remains authoritative for file bytes.

The implementation is synthetic-only and makes no production AMEC path claim.
