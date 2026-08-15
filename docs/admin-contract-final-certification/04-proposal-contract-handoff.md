# Proposal → Contract Handoff

The safe path is Human Proposal Accept → exact `AcceptedProposalRevision` → Contract eligibility → new Contract. Contract creation pins the accepted revision and its content hash; later mutable Proposal edits do not rewrite the Contract origin. Owner-session and Proposal/Contract regression tests prove this on PostgreSQL, and the browser register/detail flow is green.

Blank standalone Contract creation remains explicitly gated by policy. No invented legal or commercial policy was added.

