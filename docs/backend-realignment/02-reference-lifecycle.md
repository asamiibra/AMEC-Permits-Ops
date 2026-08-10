# Provisional reference lifecycle

New intake uses a controlled `AMEC-SYN-OPP-####` provisional reference when a
canonical Project is not yet known. It is retained in `provisional_reference`.
Canonicalization records `canonical_project_reference`, actor and timestamp,
sets Proposal/Contract/Permit project links, and adds a
`PROVISIONAL_TO_CANONICAL_REFERENCE` lineage edge. Existing references are
never overwritten or discarded.

Cross-project identity conflicts are typed 409 responses.
