# Client and Party Fields

The Contract page explicitly shows: Client Name, Client Company, CR No., Mobile No., PIN No., and Client Email. Client Name and Company resolve from the canonical Client account; Mobile and Email resolve from an active Client Contact or controlled Proposal contact context fallback; CR No. resolves from the Client account. PIN remains unresolved and safe until its semantic authority is defined.

Editing these fields uses `PATCH /api/admin/contracts/{id}/client-fields`, creates a new Contract revision, records the reason, and preserves the accepted Proposal revision unchanged.
