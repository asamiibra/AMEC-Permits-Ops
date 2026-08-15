# Stage-gate root cause

The golden fixture was created directly with `Opportunity.status = PROPOSAL_PREPARATION` in `backend/app/seed/cli.py`, then ingested a legacy `ProjectArtifactRecord`. Intake readiness checks the Proposal Register source model `ProposalSourceEvidence`, so the fixture appeared progressed but incomplete. It had bypassed both the current source seam and the real `/api/bd/proposals/{id}/proceed` command.

The repair seeds the Proposal in `IN_REVIEW`, creates current verified `ProposalSourceEvidence`, and calls the real `proceed_to_engineering` command. The projection now exposes `stage_gate.intake` and stage history, while legacy inconsistent records are explicitly marked `RECONCILIATION_REQUIRED`.
