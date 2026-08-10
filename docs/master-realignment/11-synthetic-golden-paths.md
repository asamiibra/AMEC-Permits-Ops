# G10 — Synthetic golden paths

The verified local path is Tender Email → provisional Proposal → intake SOR read-back → Proposal detail → Proceed → Engineering Proposal Preparation. The seeded path retains Proposal/Quotation → Contract → PermitApplication lineage. Duplicate source hashes reuse records; new hashes create versions; project-reference mismatch and SOR-unavailable cases are fail-closed.

Full multi-permit production cardinality remains supported by the existing PermitApplication model and is not collapsed by the new Contract link.
