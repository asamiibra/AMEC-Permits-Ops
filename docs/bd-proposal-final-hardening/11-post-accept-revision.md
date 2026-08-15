# Post-Accept revision

After Accept, the Owner can create one explicit draft `ProposalRevision` from the latest accepted snapshot. It stores base accepted revision, revision number, change summary, snapshot, content hash, creator, and status. Repeated creation is idempotent while a draft exists; later Accept supersedes only through a new immutable accepted revision.
