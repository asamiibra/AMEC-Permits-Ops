# Reference, save, output

Proposal references use the locked `MasterContentReferenceSequence` service with prefix `AMEC-SYN-PROP`, four-digit padding, max-existing synchronization, and PostgreSQL row locking. Dashboard’s four-library numbering preview intentionally excludes the Proposal sequence.

Draft PATCH supports optimistic concurrency with `expected_updated_at`; the UI shows Draft save state and a before-unload guard. Outputs remain synthetic text artifacts with explicit format/renderer/read-back lineage, revision naming, and supersession through accepted revision history.
