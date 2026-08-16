# Bad demo delta

The prior post-Dashboard evidence records `seed_started=false`, `seed_commit=null`,
and all synthetic status counts as `NOT_RUN`. There is no demo-seed commit and
no prior commit containing the invented Current/Needs Review/Inactive examples.
The post-dashboard main evidence commit only records the external deployment
blocker and does not change application code or database data.

The currently reachable Vercel database nevertheless contained five active
Forms before this repair: three ProposalOps functional masters and two generic
seed-owned rows, `Consultant Form` (`F-0001`) and `Authorization Form`
(`F-0002`). The generic rows are attributable to the existing
`reconcile_owner_demo_dataset` bootstrap (`owner-demo` source filenames), not
to an executed FORME status-demo phase.

No invented inactive FORME row, named `Synthetic ...` row, FORME binary copy,
or source-package database import was found. The surgical delta is therefore
bootstrap reconciliation plus safe archival of the two proven obsolete
generic placeholders; no whole-run revert is applicable.

`BAD_DEMO_CHANGESET_IDENTIFIED=1`.
