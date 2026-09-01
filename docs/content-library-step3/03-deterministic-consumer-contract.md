# Deterministic consumer contract

Reusable workflow selection is allowed only after the shared seam verifies: exact content type, active module binding and purpose, item ACTIVE, `needs_review=false`, current pointer, version metadata `master_status=CURRENT`, `DocumentApprovalState.REVIEWED`, source reference available, applicable governance readiness, and endpoint role authorization.

The resolver returns every eligible candidate. One candidate is `RESOLVED`; zero is `UNRESOLVED`; more than one is `AMBIGUOUS`. No consumer applies first-row-wins, similarity, filename matching, or AI inference.

Durable workflow artifacts bind exact IDs and hashes; a source update triggers existing revalidation behavior or leaves the historical artifact unchanged.
