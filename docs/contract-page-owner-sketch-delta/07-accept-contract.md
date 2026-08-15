# Accept Contract

`POST /api/admin/contracts/{id}/accept` is the explicit Owner-facing acceptance command. It requires `CONTRACT_AUTHORITY_ACTION`, resolves the current readiness configuration, and finalizes exactly the current `ContractRevision`. It records `ADMIN_CONTRACT_ACCEPTED` with actor, timestamp, revision, reason, and idempotency key.

Repeated acceptance of the finalized current revision returns `ALREADY_ACCEPTED` without a duplicate audit action. Engineering/BD roles are denied. A finalized revision is immutable through the existing prospective-amendment rule. Acceptance does not activate a Project, create an Invoice, create a Payment, or create a BillingMilestone; Project Activation remains a separate visible Owner action.
