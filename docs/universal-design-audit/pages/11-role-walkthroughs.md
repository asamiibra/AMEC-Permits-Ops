# Role Walkthroughs

## ROUTE / PERSONAS

Owner, Business Development, Engineering; no Permit Preparer, Commercial Approver, or four-assistant persona remains in current UI.

## DESIGN CONTRACT

Owner administers and oversees; Business Development owns commercial intake/review/client response; Engineering owns technical preparation and Permit technical actions. Human submission remains outside machine capability.

## DESIGN PASS / FUNCTION PASS

Role matrix passes all 9 checks: Owner Administration access, BD/Engineering Administration denial, commercial access, and downstream Permit context for all three personas.

## DATA / ROLE / INTEGRATION

Role storage maps current UI personas to backend capability values. Actions are context-only where the current persona lacks authority.

## ERROR / LOADING / EMPTY / MOBILE / ACCESSIBILITY

No local universal technical leakage or overflow was found in any applicable persona combination. Broader failures using `PERMIT_PREPARER` are stale owner-model assertions.

## CROSS-PAGE / DEFECTS / EVIDENCE

Evidence: `role-matrix-result.json`, targeted 28/28 historical suite result, and persona screenshots under `screenshots/`.
