# Client, contact, and origin proof

The Proposal workspace now captures the complete intake field set, keeps lead origin separate from evidence source family, and persists Proposal Contact through /api/bd/proposals/{id}/contact.

Canonical Client accounts are selectable through /api/bd/proposals/clients. New Client creation is an explicit /api/bd/proposals/clients command; deployed environments reject an unmatched free-text client rather than implicitly creating a canonical identity. Existing synthetic regression fixtures retain their TEST-only compatibility path.
