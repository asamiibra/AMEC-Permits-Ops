# Proposal stage and action contract

`Opportunity.status` is the canonical lifecycle state. `proposal_stage()` translates that state to the display stage and `proposal_next_action()` produces the single current action.

Existing Contract lineage has precedence: the Proposal action is `View Contract`. Intake and review states expose `Proceed` only when current source evidence exists. Handover and commercial states expose `Contract` only when eligible. The API returns eligibility and a disabled reason; the UI does not guess.
