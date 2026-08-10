# Demo Data Lineage

The seeded golden chain is `SYN-CLIENT-001 → SYN-OPP-0001 → SYN-CTR-0001 → GHCE-2026-0142 → GHCE-APP-0142`. PostgreSQL checks confirm the Opportunity, Contract, and Permit all point to the same canonical Project; Contract-to-Project, Permit-to-Project, and Permit-to-controlling-Contract checks are true.

Baseline counts: 1 client account, 1 opportunity, 1 contract, 4 projects, 4 permit applications, 11 workflow tasks, 6 findings, 4 notification events, and 3 canonical project artifact records. Fixture metadata is synthetic-only and uses the canonical fixture manifest.
