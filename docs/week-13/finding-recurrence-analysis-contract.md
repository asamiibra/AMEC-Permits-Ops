# Finding recurrence analysis contract

`POST /api/recurrence/analyze` creates `FindingRecurrenceAnalysisRun` and `FindingRecurrenceAnalysisItem` records. Classifications are `FIRST_OCCURRENCE`, `REPEATED_OPEN_ISSUE`, `RECURRENCE_AFTER_VERIFIED_CLOSURE`, `REOPENED_SAME_FINDING`, `RELATED_PRIOR_ISSUE`, and `POSSIBLE_RECURRENCE_NEEDS_REVIEW`.

The analysis preserves Finding, SubmissionCycle, PreparationRevision, Package, Approval, Resolution, and evidence identifiers. Historical Findings and closure records are immutable; links are additive audit records.
