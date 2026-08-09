# Prior Finding preventive check

`POST /api/preparation-revisions/{revision_id}/preventive-check` creates a bounded check before package/resubmission gates. Results are `NO_RELEVANT_HISTORY`, `PRIOR_ISSUE_RESOLVED_NO_CURRENT_SIGNAL`, `RECURRENCE_WATCH`, `CURRENT_UNRESOLVED_PRIOR_ISSUE`, and `POSSIBLE_RELEVANCE_NEEDS_REVIEW`.

Closed history alone is informational/watch context. Existing unresolved blocking Findings remain blocking through the Week 10 gate; no new legal or professional rule is inferred.
