# KPI predicate contract

For the full filtered work projection:

- **Needs Action**: `ACTION`, `HANDOFF`, `BLOCKER_ACTION`, or send-ready `COMMUNICATION`; review-only items are excluded.
- **Waiting for Review**: `REVIEW`.
- **Blocked**: `blocking == true`.
- **Overdue**: a configured `due_at` is before the current time and the item is not done.

`/api/work` computes the summary and the filtered list from the same item collection. The targeted backend tests run all four predicates for Owner, Business Development, and Engineering and assert the selected KPI count equals the corresponding filtered list length.

No due date is invented when a source record has no configured due rule.
