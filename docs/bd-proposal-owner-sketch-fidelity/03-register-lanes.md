# Register lanes

The lane registry is derived from current lifecycle state plus validation, readiness, intake blockers, and the configured human Proposal Accept authority.

- All: every accessible row.
- Need Action: any active validation/readiness/intake blocker, or a Client Response follow-up state.
- Authority Review: commercial review lifecycle (`PROPOSAL_HANDOVER`, `COMMERCIAL_REVIEW`, `QUOTATION_IN_PROGRESS`) with no active blocker and human Accept authority required.
- Ready / Close: `CLIENT_RESPONSE_PENDING`, `ACCEPTED`, `CONTRACT_HANDOVER`, or `CLOSED` with no active blocker.

Counts and filtered rows use the same `owner_lane.memberships` predicate in the list projection. These are operational views, not persisted lifecycle states; `AUTHORITY_REVIEW` is not an Opportunity enum and never creates an AuthorityCase.

Policy-dependent items remain explicit: the exact configured Accept authority and any future Ready / Close policy may change through the existing Owner decision registry. The current safe runtime policy is surfaced as human-readable authority copy.
