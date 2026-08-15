# Lifecycle and next action

Owner-facing mapping for the current and target semantic states:

`IN_REVIEW` → Intake & Sources / Business Development / Proceed when ready.

`PROPOSAL_PREPARATION` or equivalent → Engineering Preparation / Engineering / Open preparation.

`PROPOSAL_HANDOVER` / engineering-ready → Commercial Review / Business Development / Review current Proposal revision.

`COMMERCIAL_REVIEW`, `READY_FOR_RELEASE`, `RELEASED` → Commercial Review or Client Response according to the exact current state.

`CLIENT_RESPONSE_PENDING` → Client Response / Business Development / Record response.

`ACCEPTED` or Contract-eligible accepted revision → Contract Handoff / configured Contract authority / Handoff exact accepted revision.

The frontend must derive next action from backend state and readiness; it must not infer Contract, Project, or Permit actions from a badge.
