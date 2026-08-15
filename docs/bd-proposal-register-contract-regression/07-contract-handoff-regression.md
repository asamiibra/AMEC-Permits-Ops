# Proposal → Contract regression

The register retains `ACCEPTED` and `CONTRACT_HANDOVER` as valid Proposal lifecycle states. Contract-eligible state, owner lane, next action, and validation remain response fields rather than frontend guesses. Existing accepted-revision and Contract owner-session coverage passed on PostgreSQL, and the browser opened the Contract Handoff Proposal detail without the global recovery shell.

The current synthetic snapshot contains one Engineering Preparation Proposal and one Contract Handoff Proposal. Both are visible in All and Need Action; the current snapshot has no Authority Review or Ready / Close rows because both have active blockers.
