# Cross-module regression

Accepted Proposal revision remains the only origin for Contract Handoff. Contract, Project, AuthorityCase, and activation seams remain explicit downstream operations. No automatic Contract or Project activation was added by this hardening.

Verification: repository-root SQLite suite passed 209 with 8 skipped; Proposal-focused PostgreSQL suite passed 11 with 0 failures; the relevant browser regression group passed 5 with 0 failures. The broader PostgreSQL suite retains the documented unrelated fixture contamination caveat.
