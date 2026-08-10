# Static business-state audit

The audit found remaining static or fallback business-looking state in legacy presentation paths. These are not counted as completed workflow commands:

1. `projectNextAction()` retains a compatibility fallback when the detail projection is unavailable.
2. `WorkspaceStage` renders generic “Current state” and “Blockers” copy without a stage-specific persisted state response.
3. `FinalReviewStage` renders a static checklist rather than a server-evaluated gate result.
4. `AuthorityReviewStage` uses a returned-state fallback count when monitoring history is unavailable.
5. Several legacy list screens use catch-to-empty behavior, which can make an API outage look like an empty business result.

Stage 1 is protected because its workspace refresh requires a valid workflow projection and findings array; a malformed response is shown as an error rather than converted to fake empty data. The remaining findings are blockers to the whole-app completion decision.
