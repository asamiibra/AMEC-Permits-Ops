# Stage 2 capability disposition contract

Stage 1 v2.6 requirements are not capability approval. A capability moves through explicit states: `REQUIREMENT_EXISTS`, `CAPABILITY_DESIGNED`, `CAPABILITY_IMPLEMENTED`, `CAPABILITY_TESTED`, `CAPABILITY_APPROVED_FOR_BUILD`, and `CAPABILITY_APPROVED_FOR_PRODUCTION`.

The E0 registry uses `UNDECIDED_STAGE2` for every current disposition because no signed Stage 2 approval is present in the repository. The four assistant identifiers are bounded presentation/capability routes over shared PermitOps entities; they are not autonomous agents and do not own truth, approvals, tasks, audit, or lineage.

The typed foundation is in `backend/app/expansion/governance.py` and the E1 database representation is `AssistantCapabilityDefinition`. No seeded record claims owner approval, build approval, or production approval.
