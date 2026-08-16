# Current record reconciliation

Entry API inspection found three current ProposalOps functional masters:
`AMEC Proposal Template`, `AMEC Proposal Checklist`, and `AMEC Contract
Template`. It also found the two generic placeholder rows `F-0001` and
`F-0002`.

The repair removes the generic rows from future bootstrap creation and
archives them only when their ownership markers prove they were created by
the old owner-demo seed, have only `AVAILABLE` bindings, and have no direct
consumer/dependency references. The archive operation preserves the
MasterContentItem, Document, DocumentVersion, audit, and history records.

The repair adds the exact seven Current and seven Needs Review FORME business
projections with stable identity and idempotent seed keys.
