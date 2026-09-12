# ProposalOps / AMEC Billing current-main integration closure

The historical Billing seal was verified before integration. The exact recovered tree remains `4fa639431a44ffbeb07f65a135272d9209f65c34`; the missing historical commit object remains intentionally unrecovered.

The exact 28-path historical delta was classified. Nine Billing/related source-test paths were carried forward; three independently changed test files were semantically merged; 19 generated/evidence/platform paths were excluded. The Billing migration was forward-ported as a child of current `source18_committee_implementation_v1`, producing one Alembic head.

Current-main causal requalification passed for the Billing-focused backend suite, AI/API authority suite, real PostgreSQL concurrency probe, populated browser journey, independent persistence readback, frontend tests/build, migration graph, and hostile negative matrix. The control/candidate full regression A/B reproduced the same shared `source_preflight.py` harness timeout, and the separate Source18 A/B reproduced the same pre-Billing PostgreSQL baseline/index blockers. Neither was caused by the Billing delta.

The branch is not merged or deployed. No production, Azure, Entra, preprod, bank, or real AMEC financial data was touched.
