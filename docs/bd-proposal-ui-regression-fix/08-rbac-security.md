# RBAC and security

The change keeps the existing capability checks. Register/detail reads use the Proposal read capability; Proposal creation and source intake use the Proposal write capability. The frontend role header is only the existing synthetic-development mechanism; it is not an authorization bypass. Server-side capability checks remain authoritative.

Source files are handled through the existing source-registration path. The initial source endpoint validates the typed source, requires a non-empty upload, links it to the newly created Proposal, and rolls back on failure. No new migration or production-ready token was introduced.
